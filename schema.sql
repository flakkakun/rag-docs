create extension if not exists vector;

create table chunks (
  id        bigserial primary key,
  source    text not null,           -- file the chunk came from, used for citations
  position  int  not null,           -- chunk number within that file
  content   text not null,
  embedding vector(384) not null,    -- bge-small-en-v1.5 outputs 384 numbers
  tsv       tsvector generated always as (to_tsvector('english', content)) stored
);

-- HNSW graph for vector search. m = links per node, ef_construction = how hard
-- it searches for good links while building. Higher = better recall, slower build.
create index chunks_embedding_hnsw on chunks
  using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64);

-- Inverted index for keyword search: word -> list of chunks containing it.
create index chunks_tsv_gin on chunks using gin (tsv);

-- How many chunks contain each word, refreshed by ingest.py. BM25 needs this
-- to weight rare words ("Orca", 1 chunk) above common ones ("use", most chunks).
create table term_stats (
  term text primary key,
  ndoc int  not null
);
