Sam: Chapter six. PagedAttention, vLLM, and SGLang. Maya, set up the problem for me.

Maya: Okay. Remember, every user has a KV cache, and it grows by one token's worth every time a new token is generated. The problem is, when a request arrives, you don't know how long the answer will be. Could be ten tokens. Could be two thousand.

Sam: So how much memory do you set aside?

Maya: That's the problem. Before vLLM, the common approach was to reserve one big continuous block of memory per request, sized for the maximum possible length. If the model allows four thousand tokens, you reserve space for four thousand tokens, even if this user only ends up needing two hundred.

Sam: That sounds incredibly wasteful.

Maya: It was. The vLLM researchers, at UC Berkeley, measured existing systems in their 2023 paper, and found that the majority of KV cache memory, they reported somewhere around sixty to eighty percent, was being wasted. Reserved but empty, or stuck in awkward gaps between blocks that were too small to use.

Sam: Like a parking lot where every car takes up a space big enough for a bus.

Maya: Exactly like that. And remember, KV cache memory is what decides how many users you can serve. So wasting most of it means serving a fraction of the users you could.

Sam: So what was their idea?

Maya: They borrowed an idea from operating systems that's been around since the 1960s: virtual memory with paging. Your laptop does this all the time. When a program asks for memory, the operating system doesn't give it one giant continuous block. It hands out small fixed-size pages, wherever there's free space, and keeps a table that maps the program's view of memory to where the pages actually are.

Sam: So the program thinks it has one neat continuous chunk, but really it's scattered all over.

Maya: Exactly. PagedAttention does the same thing for the KV cache. The cache is split into small blocks, each holding the keys and values for, say, sixteen tokens. When a request starts, it gets one block. When that block fills up, it gets another one, from wherever there's free space. A small table keeps track of which blocks belong to which request, in what order.

Sam: So nobody reserves space for a bus. You get a new parking space every sixteen tokens, only when you need it.

Maya: And when a request finishes, its blocks go straight back into the pool for someone else. The waste drops to almost nothing. The paper reported under four percent. And because memory is no longer wasted, the engine can fit many more requests into the same batch, which, as we learned, means much higher throughput. The paper reported two to four times the throughput of the best systems at the time.

Sam: That's a huge jump from one idea.

Maya: It's a great example of a classic computer science idea solving a brand new problem. And there's a bonus. Because blocks are tracked in a table, two requests can share the same blocks. If a hundred users all start with the same long system prompt, you only need to store that prompt's KV cache once, and everybody points to it.

Sam: So that's why it's called vLLM. The V is about virtual memory.

Maya: That's the connection most people make, yes. The core idea is managing the KV cache the way an operating system manages virtual memory.

Sam: Okay, and the other name in our project brief was SGLang. Where does that fit?

Maya: SGLang is another open-source inference engine, also from researchers connected to Berkeley and the LMSYS group. It does continuous batching and paged memory too, but its signature idea is called RadixAttention, which pushes that sharing bonus much further.

Sam: How so?

Maya: SGLang keeps the KV cache from previous requests around, organized in a tree structure called a radix tree, indexed by the text that produced it. When a new request comes in, it looks for the longest beginning that matches something it has already computed, and reuses that cache instead of redoing the prefill.

Sam: When would that matter?

Maya: All the time, in real apps. A chatbot where every message re-sends the whole conversation so far. An agent that calls the model fifty times with the same instructions at the top. A RAG system that sends the same documents with different questions. In all of those, most of the prompt is repeated, and SGLang can skip recomputing it. That cuts prefill time, which cuts time to first token.

Sam: Isn't vLLM also doing prefix caching these days?

Maya: It is. Both engines have borrowed heavily from each other. Today they're close competitors, and which one is faster depends on your model, your hardware, and your traffic pattern. That's why one of the experiments planned for our project is to run the exact same benchmark on both and compare. That's the kind of thing that turns a portfolio project into a real engineering story. You're not saying "I've heard of SGLang." You're saying "I measured it on my workload, and here's what I found."

Sam: Let me give the interview version. vLLM is an open-source inference engine. Its key idea, PagedAttention, stores the KV cache in small fixed-size blocks, like operating system memory pages, instead of one big reserved chunk per request. That cuts wasted memory from most of it to almost none, so it can batch many more requests and get much higher throughput. SGLang is a competing engine whose signature idea, RadixAttention, reuses the KV cache for repeated prompt beginnings, which speeds up chat, agents, and RAG.

Maya: That is a really strong answer. Now let's talk about how you measure whether any of this is working.
