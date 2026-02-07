# Hierarchical Entity Caching in Redis with Semantic Keys

## Technical Design Document

**Author**: AndI Architecture Team
**Status**: Draft
**Date**: February 2026

---

## 1. Problem Statement

Modern agent-driven architectures need to cache hierarchical data — entities that contain other entities, collections that group them, and metadata that describes their shape and relationships. Traditional flat key-value caching breaks down when agents need to traverse hierarchy, when clients need server-driven UI configuration, and when the cache itself needs to serve as a source of truth for data patterns.

The core challenge: how do you cache deeply nested, relationally-aware data in Redis while keeping keys human-readable, hierarchy traversable, and metadata rich enough that agents can reason about the data without hitting the database?

---

## 2. Key Design Principles

### 2.1 Semantic Key Naming Convention

Every Redis key encodes meaning. An agent or engineer reading the key should understand what it points to without looking it up.

**Key Format**: `{namespace}:{entity_type}:{identifier}:{aspect}`

Examples:
```
app:user:u_8f3k2:profile          → User profile entity
app:user:u_8f3k2:settings         → User settings entity
app:org:org_acme:members          → Collection of org members
app:org:org_acme:_meta            → Metadata about the org entity
app:component:sidebar_nav:spec    → UI component specification
app:component:sidebar_nav:_schema → Component's data schema
```

**Collection Keys**: `{namespace}:{parent_type}:{parent_id}:_{collection_name}`

```
app:org:org_acme:_teams           → Set of team IDs under this org
app:team:team_alpha:_members      → Set of user IDs in this team
app:project:proj_x:_tasks         → Sorted set of task IDs (by priority)
```

### 2.2 Two Entity Types

The system distinguishes between **entities** and **collection entities**.

**Entity**: A discrete object with properties. Stored as a Redis hash.
```redis
HSET app:user:u_8f3k2:profile
  name "Jordan Chen"
  email "jordan@acme.co"
  role "engineer"
  _parent "app:org:org_acme"
  _type "user"
  _version 14
  _updated_at "2026-02-06T18:30:00Z"
```

**Collection Entity**: An ordered or unordered group of entity references. Stored as a Redis sorted set or set.
```redis
ZADD app:org:org_acme:_teams 1 "app:team:team_alpha" 2 "app:team:team_beta" 3 "app:team:team_gamma"
```

The `_parent` field in every entity creates an implicit tree. The collection keys create explicit groupings. Together they form a navigable hierarchy.

---

## 3. Hierarchy Traversal via MCP

### 3.1 MCP Tool Definitions

Agents access the cache through MCP (Model Context Protocol) tools. Three core traversal operations:

**`cache_get`** — Read a single entity or collection.
```json
{
  "tool": "cache_get",
  "params": {
    "key": "app:user:u_8f3k2:profile"
  }
}
```

**`cache_traverse`** — Walk the hierarchy up or down.
```json
{
  "tool": "cache_traverse",
  "params": {
    "start": "app:org:org_acme",
    "direction": "down",
    "depth": 2,
    "filter": { "entity_type": "user" }
  }
}
```

This returns all users under the org, traversing through teams. The agent does not need to know the intermediate structure — the cache layer handles it by following `_parent` back-references and collection set memberships.

**`cache_query`** — Pattern-based key search with metadata filtering.
```json
{
  "tool": "cache_query",
  "params": {
    "pattern": "app:component:*:spec",
    "where": { "_type": "component", "platform": "ios" }
  }
}
```

### 3.2 Agent Traversal Patterns

Agents build mental models of the data hierarchy by traversing the cache. Common patterns:

1. **Root Discovery**: `SCAN 0 MATCH app:*:_meta` to find all top-level entity types
2. **Collection Enumeration**: `SMEMBERS app:org:org_acme:_teams` to list children
3. **Upward Walk**: Read `_parent` field, follow the key, repeat until no parent
4. **Breadth-First Scan**: At each level, read all collection keys, expand one level
5. **Schema Introspection**: Read `{key}:_schema` to understand an entity's shape without reading all fields

### 3.3 Why Agents Need This

Traditional database queries require the agent to know SQL, understand joins, and handle connection pooling. With the cache hierarchy:

- Agents traverse data using simple key operations
- No SQL knowledge required — just follow keys and parent pointers
- Schema metadata tells the agent what fields exist and their types
- The cache is the agent's working memory for the data domain

---

## 4. Metadata Layer — SQL Patterns as Source of Truth

### 4.1 Schema Metadata

Every entity type has a `_schema` key that describes its structure:

```redis
HSET app:_schemas:user
  fields '["name","email","role","department","hire_date"]'
  types '{"name":"string","email":"string","role":"enum:engineer,manager,director","department":"fk:department","hire_date":"date"}'
  sql_table "users"
  sql_primary_key "id"
  sql_select "SELECT id, name, email, role, department_id, hire_date FROM users WHERE id = $1"
  sql_list "SELECT id FROM users WHERE org_id = $1 ORDER BY name"
  sql_search "SELECT id FROM users WHERE org_id = $1 AND (name ILIKE $2 OR email ILIKE $2)"
  _indexes '["email_unique","org_department_idx"]'
  _relations '{"department":{"type":"belongs_to","target":"department","fk":"department_id"},"teams":{"type":"has_many_through","target":"team","through":"team_members"}}'
```

### 4.2 SQL Pattern Registry

The cache stores canonical SQL patterns that agents can use as templates:

```redis
HSET app:_sql_patterns:user:list
  query "SELECT u.id, u.name, u.email, u.role FROM users u WHERE u.org_id = $1 ORDER BY u.name LIMIT $2 OFFSET $3"
  params '["org_id","limit","offset"]'
  returns "user[]"
  cache_key_template "app:org:{org_id}:_users:page:{offset}"
  ttl 300
  invalidated_by '["user:create","user:update","user:delete"]'
```

This means an agent can:
1. Look up the SQL pattern for "list users in an org"
2. See exactly what query to run
3. Know which cache key to check first
4. Understand when the cached result becomes stale

### 4.3 Reverse Engineering from Cache

If an agent encounters an unfamiliar entity, it can reverse-engineer its structure:

1. Read `app:_schemas:{entity_type}` for field definitions
2. Read `app:_sql_patterns:{entity_type}:*` for all query patterns
3. Read `_relations` to understand joins and foreign keys
4. Read `_indexes` to understand query performance characteristics

This makes the cache self-documenting. An agent dropped into the system with no prior knowledge can discover the entire data model by scanning schema keys.

---

## 5. Component Registry — Server-Driven UI Configuration

### 5.1 Component Entity Structure

UI components are cached as entities with full specifications:

```redis
HSET app:component:user_profile_card:spec
  component_id "user_profile_card"
  version 3
  platform '["ios","android","web"]'
  layout '{"type":"card","padding":16,"cornerRadius":12}'
  slots '["avatar","name","role","actions"]'
  data_bindings '{"avatar":"user.profile_image_url","name":"user.name","role":"user.role"}'
  actions '["edit_profile","send_message","view_activity"]'
  variants '{"compact":{"slots":["avatar","name"]},"expanded":{"slots":["avatar","name","role","actions","bio"]}}'
  _parent "app:component_group:profile_section"
  _type "component"
  _updated_at "2026-02-06T12:00:00Z"
```

### 5.2 Component Tree (Server-Driven Layout)

The component hierarchy in Redis mirrors the UI tree:

```
app:screen:home_screen:spec
  └── app:component_group:header:spec
  │     └── app:component:logo:spec
  │     └── app:component:search_bar:spec
  │     └── app:component:notification_bell:spec
  └── app:component_group:main_feed:spec
  │     └── app:component:feed_item:spec (template, reused N times)
  └── app:component_group:bottom_nav:spec
        └── app:component:nav_item_home:spec
        └── app:component:nav_item_search:spec
        └── app:component:nav_item_profile:spec
```

Collection keys link them:
```redis
ZADD app:screen:home_screen:_groups 1 "app:component_group:header" 2 "app:component_group:main_feed" 3 "app:component_group:bottom_nav"
ZADD app:component_group:header:_components 1 "app:component:logo" 2 "app:component:search_bar" 3 "app:component:notification_bell"
```

### 5.3 Client Configuration Protocol

The client fetches its UI configuration from the cache in one round-trip:

```
GET /api/v1/screens/home_screen/config
```

The server:
1. Reads `app:screen:home_screen:spec` from Redis
2. Traverses down through `_groups` → `_components`
3. Resolves all component specs
4. Returns the full component tree as JSON
5. Includes a `_cache_version` hash for client-side diffing

The client renders the UI from this spec. When the server updates a component, the client gets the diff on next poll (or via WebSocket push).

### 5.4 Why This Matters for Server-Driven Configuration

- **No app store updates** needed for UI changes
- **A/B testing** by serving different component trees to different users
- **Agent-modifiable UI** — agents can propose layout changes by modifying cached specs
- **Component reuse** — the same component spec serves iOS, Android, and web
- **Versioned rollback** — every spec has a version, roll back by decrementing

---

## 6. Cache Invalidation Strategy

### 6.1 Write-Through with Cascade

When an entity changes:
1. Write to database (source of truth)
2. Update the Redis cache entry
3. Cascade invalidation to parent entities that aggregate this data
4. Publish invalidation event to subscribed agents

```python
async def invalidate_entity(key: str):
    """Cascade invalidation up the hierarchy."""
    entity = await redis.hgetall(key)
    parent_key = entity.get("_parent")

    # Invalidate this entity's cache
    await redis.delete(key)

    # Invalidate any collection caches that include this entity
    entity_type = entity.get("_type")
    await redis.delete(f"{key}:_collections_cache")

    # Cascade to parent
    if parent_key:
        await invalidate_entity(parent_key)

    # Publish event for agent subscribers
    await redis.publish(f"invalidation:{entity_type}", key)
```

### 6.2 TTL Strategy

| Entity Type | TTL | Rationale |
|-------------|-----|-----------|
| User profiles | 5 min | Moderate change frequency |
| Org structure | 30 min | Rarely changes |
| Component specs | 1 hour | Only changes on deploy |
| SQL patterns | 24 hours | Changes only on schema migration |
| Schema metadata | No TTL | Invalidated explicitly on migration |

### 6.3 Consistency Guarantees

- **Strong consistency** for single-entity reads (write-through)
- **Eventual consistency** for collection aggregations (TTL-based refresh)
- **Causal consistency** for agent traversals (version checks at each hop)

---

## 7. Redis Data Structure Mapping

| Concept | Redis Type | Key Pattern |
|---------|-----------|-------------|
| Entity | Hash | `{ns}:{type}:{id}:{aspect}` |
| Collection (ordered) | Sorted Set | `{ns}:{type}:{id}:_{collection}` |
| Collection (unordered) | Set | `{ns}:{type}:{id}:_{collection}` |
| Schema | Hash | `{ns}:_schemas:{type}` |
| SQL Pattern | Hash | `{ns}:_sql_patterns:{type}:{operation}` |
| Invalidation channel | Pub/Sub | `invalidation:{type}` |
| Cache version | String | `{ns}:{type}:{id}:_version` |

---

## 8. Implementation Considerations

### 8.1 Memory Estimation

For a system with 100K entities across 20 types:
- Entity hashes: ~100KB each = ~10GB
- Collection sets: ~1KB each = ~100MB
- Schema metadata: ~50KB total (20 types)
- SQL patterns: ~200KB total
- **Total**: ~10-12GB (fits in a single Redis instance with 16GB)

### 8.2 Performance Characteristics

- Single entity read: <1ms (Redis hash GET)
- Collection enumeration: <2ms (SMEMBERS/ZRANGE)
- Full hierarchy traversal (3 levels): <10ms (pipelined)
- Schema introspection: <1ms (cached in local agent memory after first read)
- Pattern-based key scan: 5-50ms depending on keyspace size

### 8.3 Monitoring

Key metrics to track:
- Cache hit ratio per entity type
- Average traversal depth per agent query
- Invalidation cascade depth and frequency
- Memory usage per entity type
- Stale read rate (reads that return expired data before TTL)

---

## 9. Security Model

- **Namespace isolation**: Different tenants use different key prefixes
- **Agent ACLs**: Redis ACLs restrict which key patterns each agent can read/write
- **Audit logging**: All write operations log the agent ID and timestamp
- **Encryption at rest**: Redis configured with TLS for data in transit, RDB encryption for persistence

---

## Summary

This design gives you a Redis cache that is simultaneously:
1. **A fast data store** with sub-millisecond reads
2. **A navigable hierarchy** that agents can traverse without SQL
3. **A schema registry** that makes the data model self-documenting
4. **A component registry** for server-driven UI configuration
5. **A source of truth** for data patterns and SQL templates

The semantic key convention means any engineer or agent can read a Redis key and immediately understand what it represents. The hierarchy traversal via MCP means agents interact with structured data through simple tool calls. The metadata layer means the cache documents itself — no external wiki needed to understand the data model.
