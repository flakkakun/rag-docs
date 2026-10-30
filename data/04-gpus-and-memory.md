Sam: Chapter four. Why GPUs are waiting on memory, not math. Maya, explain this to me like I've never thought about it, because I haven't.

Maya: Let's start with what a GPU actually is. A GPU is a chip with thousands of small processors that all do simple math at the same time. That's why they were made for graphics, millions of pixels at once, and it's why they're great for AI, which is mostly huge amounts of multiplication.

Sam: Okay, so lots of math, in parallel.

Maya: Right. But the math needs numbers to work on. Those numbers, the model weights and the KV cache, live in the GPU's memory. And before the processors can multiply anything, they have to read those numbers out of memory. The speed of that reading is called memory bandwidth.

Sam: And how fast is that?

Maya: On the L4 we used, about three hundred gigabytes per second. Which sounds enormous. But think about what happens when the model generates a single token.

Sam: It runs the whole model once.

Maya: It runs the whole model once. Which means it has to read all fifteen gigabytes of weights out of memory. Every single token. So, three hundred gigabytes a second, divided by fifteen gigabytes per token...

Sam: Twenty. Twenty tokens per second.

Maya: That's the speed limit. Roughly twenty tokens a second for a single user on that card, no matter how fast the math units are. In practice a bit less, because there's overhead. And notice something. That's about fifty milliseconds between each token.

Sam: Fifty milliseconds. And that's the inter-token latency we're going to measure.

Maya: Exactly. We can predict it before we even run the benchmark, just from two numbers on a spec sheet: the size of the model and the memory bandwidth of the GPU. That's a really powerful thing to be able to say in an interview.

Sam: But hold on. If the math units are sitting idle while memory is being read, isn't the GPU mostly wasted?

Maya: For one user? Yes. Badly. The GPU reads fifteen gigabytes of weights, uses each number for one tiny multiplication for one user's token, and then throws it away and reads it all again for the next token. The math units are bored. Engineers describe this by saying generation is memory-bound.

Sam: So how do you fix that?

Maya: Here's the beautiful part. While you've got those weights loaded, you could use them for more than one user. If thirty users are all waiting for their next token, you read the weights once and do the math for all thirty of them at the same time. Reading the weights costs about the same. The math units finally have something to do.

Sam: So thirty users cost roughly the same time per step as one user?

Maya: Not exactly the same, because each user also has their own KV cache to read, but close enough that the total output can go up enormously. That's batching, and it's the single biggest reason one GPU can serve many people. It's the whole next chapter.

Sam: Before that, I've also heard the words prefill and decode. Where do those fit?

Maya: Great, those are the two phases of every request. When your prompt first arrives, the model has to process all of it. Say your prompt is five hundred tokens. The good news is, all five hundred are already known, so the model can process them all at once, in parallel. That's the prefill phase. It's heavy on math, and GPUs are great at it.

Sam: And then decode is the one-token-at-a-time part.

Maya: Exactly. Decode is generating the answer, token by token, and that's the memory-bound part we just talked about. So prefill is compute-bound, decode is memory-bound. Two very different workloads living inside the same request.

Sam: And which one decides the time to first token?

Maya: Prefill, mostly. Time to first token is how long you wait before you see anything. That's the time to process your whole prompt, plus any time waiting in a queue. A long prompt means a long prefill, which means a longer time to first token. Then once tokens start flowing, the gap between them is set by decode.

Sam: That's a really clean mental model. Prefill sets time to first token. Decode sets the gap between tokens.

Maya: And here's a fun wrinkle. Prefill is so heavy that if a big new prompt arrives while thirty other users are in the middle of decoding, it can stall all of them for a moment. Everybody's stream hiccups. Modern engines, including vLLM, use a trick called chunked prefill. They break big prompts into pieces and mix them in with the ongoing decode steps, so nobody gets frozen.

Sam: So the engine is constantly juggling.

Maya: Constantly. And that juggling is the art of serving. Okay, let's do a quick recap.

Sam: My turn. Generating text is limited by memory bandwidth, not math, because every token means reading all the model's weights. On an L4, fifteen gigabytes of weights at three hundred gigabytes a second gives you about twenty tokens a second for one user. The fix is to serve many users with each read of the weights, which is batching. And every request has two phases: prefill, which processes the prompt in parallel and decides time to first token, and decode, which generates one token at a time and decides the gap between tokens.

Maya: I'd hire you.
