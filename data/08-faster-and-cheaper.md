Sam: Chapter eight. Making it faster and cheaper. Maya, say I've deployed my model, I've measured my three numbers, and my boss says: make it cheaper. What are my levers?

Maya: There are a handful of big ones. Let's go through them roughly in order of how often people reach for them.

Sam: Lever one.

Maya: Quantization. Right now our model stores each of its seven billion numbers using sixteen bits, two bytes. Quantization stores them with fewer bits. Eight bits, or even four bits. At four bits, the model shrinks from about fifteen gigabytes to about five.

Sam: Doesn't that make the model dumber?

Maya: A little, but much less than you'd expect. Good quantization methods, like one called AWQ, are careful about which numbers matter most and protect those. For many tasks, a well-quantized model is very close in quality to the original. And the benefits are big.

Sam: Because of memory.

Maya: Because of memory, twice over. First, remember the speed limit: decode has to read all the weights for every token. If the weights are a third of the size, you read a third as much, so each token can come out faster. Second, the memory you saved becomes KV cache, so you can fit more users in the batch. Faster per user and more users. That's why quantization is usually the first thing people try.

Sam: And that's one of the planned experiments. Same GPU, quantized model, compare the numbers.

Maya: Exactly. You'd show the trade-off: this much faster, this many more users, and here's a quick quality check to show it still gives good answers.

Sam: Lever two.

Maya: A different GPU. And it's not always "buy the biggest one." Remember, decode speed is mostly about memory bandwidth. The L4 has about three hundred gigabytes a second. An A100 has around two thousand. An H100, over three thousand. So moving to an H100 can make each token many times faster, and it has more memory for KV cache too.

Sam: But it costs more per hour.

Maya: It does, maybe four or five times more. So the real question isn't "which is fastest?" It's "which gives me the lowest cost per million tokens while meeting my latency target?" Sometimes the expensive GPU wins because it serves so many more users. Sometimes a cheap card wins for low-traffic apps. You only know by measuring.

Sam: How do you calculate cost per million tokens?

Maya: It's simple and very useful. Take the GPU's price per hour, divide by the number of tokens it produces per hour at your chosen load. Say a GPU costs eighty cents an hour and you get four hundred tokens a second under load. That's one point four four million tokens an hour. So about fifty-five cents per million tokens.

Sam: And you can compare that against just paying an API provider.

Maya: Exactly. That's the real business question behind self-hosting. Some companies save a lot by running their own models. Others find the API is cheaper once you count engineering time and idle GPUs. Being able to work that out with real numbers is a seriously valuable skill.

Sam: Lever three.

Maya: Speculative decoding. This one is clever. Remember, decode is slow because each token needs a full pass through the big model, one after another. Speculative decoding uses a small, fast draft model to guess the next several tokens. Then the big model checks all those guesses at once, in a single pass.

Sam: And checking several tokens at once is like prefill. Parallel, so it's cheap.

Maya: Exactly. If the draft guessed the first four tokens correctly, you just got four tokens for the price of roughly one big-model step. If it guessed wrong at token two, you keep the first one and carry on. The output is exactly what the big model would have produced. It's just faster, sometimes two or three times, especially when there aren't many users and the GPU has spare math capacity.

Sam: Lever four.

Maya: Tuning the engine. vLLM has settings that matter. How much of the GPU memory it's allowed to use. The maximum context length. If you only need two thousand tokens of context, not thirty-two thousand, you leave more room for batching. How many requests it's allowed to run at once. Whether chunked prefill and prefix caching are on.

Sam: So in our project, we set the maximum context length to four thousand ninety-six, and memory use to ninety percent.

Maya: Right. Those were sensible defaults for an L4. A natural experiment would be to change one at a time and watch what happens to the three numbers. That's exactly what tuning looks like in a real job.

Sam: And lever five?

Maya: The boring one, and maybe the biggest. Don't pay for GPUs you aren't using. Scale to zero when there's no traffic, and scale up when there's a lot. Which is exactly what we set up on Modal today, and it's a perfect segue into what actually happened.

Sam: Quick recap first. Quantization shrinks the weights, which makes decoding faster and frees memory for more users. A different GPU changes your memory bandwidth and memory size, and the real measure is cost per million tokens at your latency target. Speculative decoding uses a small draft model to guess tokens that the big model checks in parallel. Engine tuning trades context length and memory for batch size. And scaling to zero stops you paying for idle GPUs.

Maya: Perfect. Now, story time.
