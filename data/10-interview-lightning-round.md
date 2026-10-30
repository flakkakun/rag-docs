Sam: Chapter ten. The lightning round. Maya is going to fire interview questions at me, and I'm going to answer them in a few sentences each, the way I'd want to in a real interview.

Maya: And listener, try answering each one in your head before Sam does. Pause if you need to. Ready?

Sam: Ready.

Maya: What's the difference between a large language model and vLLM?

Sam: The model is the trained weights, in my case Qwen 2.5 seven billion, about fifteen gigabytes. vLLM is the inference engine that loads those weights onto a GPU and serves them as an API, with batching and memory management that make it fast.

Maya: Why do language models generate text one token at a time?

Sam: Because each token depends on all the tokens before it. You can't predict the fifth word until you know the fourth. That's called autoregressive generation, and it means every token is a full pass through the model.

Maya: What is attention?

Sam: It's how the model decides which earlier tokens matter for the current one. Each token has a query, a key, and a value. The query is compared with every earlier key to get relevance scores, and the output is a weighted mix of the earlier values.

Maya: What is the KV cache, and why does it matter?

Sam: It stores the keys and values for every token the model has already processed, so they don't get recomputed for every new token. It trades memory for speed. It grows with conversation length and the number of users, and on a serving GPU it's the main limit on how many users you can batch at once.

Maya: Why is decoding memory-bound rather than compute-bound?

Sam: Because generating each token means reading all the model weights from GPU memory, but only doing a small amount of math with them. So the speed limit is memory bandwidth. On an L4, three hundred gigabytes a second divided by fifteen gigabytes of weights is about twenty tokens a second for a single user.

Maya: What's the difference between prefill and decode?

Sam: Prefill processes the whole prompt at once, in parallel, which is compute-heavy and mostly determines time to first token. Decode generates the answer one token at a time, which is memory-bound and determines the gap between tokens.

Maya: What is continuous batching?

Sam: Instead of running a fixed group of requests until they all finish, the engine adds and removes requests at every token step. Finished requests leave immediately and waiting ones join, so the GPU stays full of useful work.

Maya: What problem does PagedAttention solve?

Sam: Older systems reserved one big block of memory per request for the maximum possible length, which wasted most of the KV cache memory. PagedAttention splits the cache into small fixed-size blocks, like operating system memory pages, and hands them out as needed. Almost no waste, so many more requests fit in a batch, and throughput goes up a lot.

Maya: How is SGLang different from vLLM?

Sam: They're both open-source inference engines with continuous batching and paged memory. SGLang's signature feature is RadixAttention, which keeps and reuses the KV cache for repeated prompt beginnings, which helps chat, agents, and RAG where a lot of the prompt repeats.

Maya: Define TTFT, ITL, and throughput, and explain the trade-off.

Sam: Time to first token is the wait before the first word, and it's what makes an app feel responsive. Inter-token latency is the gap between words, which makes streaming feel smooth. Throughput is total tokens per second across all users, which sets cost. Adding more concurrent users raises throughput but makes time to first token and inter-token latency worse, so you pick a latency target and maximize throughput inside it.

Maya: Why report p ninety-nine instead of the average?

Sam: Because averages hide the slow requests. If one in a hundred users waits twenty seconds, the average can still look fine. P ninety-nine tells you what your unluckiest users experience, and that's often where the real problems show up.

Maya: Your boss says serving costs too much. What do you try?

Sam: First, measure cost per million tokens at our latency target. Then try quantization, which shrinks the weights and frees memory for more users. Tune the engine, like maximum context length, so more requests fit in a batch. Compare GPUs on cost per million tokens, not just speed. Consider speculative decoding for low-traffic latency. And make sure we scale to zero so we never pay for idle GPUs.

Maya: Last one. Tell me about a problem you hit deploying a model.

Sam: When I first benchmarked my vLLM server on Modal, the script crashed on the very first request. The cold start, downloading fifteen gigabytes of weights and loading them, took longer than the platform's request limit, so it sent back a redirect. I fixed it by having the benchmark poll vLLM's health endpoint until the model was loaded, and only then start measuring. Since then, I always build readiness checks into anything that talks to a service.

Maya: That's a great answer, because it's specific, it's true, and it shows how you think.

Sam: Maya, any final advice?

Maya: Two things. First, when you talk about this project, lead with the numbers you measured, not the tools you used. "On a single L4, I measured this time to first token at thirty-two concurrent users, and this many tokens per second" is a hundred times stronger than "I used vLLM and Grafana." Second, don't be afraid to say what broke. Real engineers break things all day. The skill is figuring out why.

Sam: That's it for Under the Hood. Go build something, measure it, and tell the story honestly.

Maya: See you next time.
