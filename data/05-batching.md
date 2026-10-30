Sam: Chapter five. Batching. Maya, we just said batching is the biggest reason one GPU can serve lots of people. Let's dig in.

Maya: Let's use a restaurant. Imagine a waiter who takes one table's order, walks to the kitchen, waits for the food, brings it out, and only then goes to the next table.

Sam: Terrible restaurant.

Maya: Terrible restaurant. That's serving one request at a time. Now imagine the waiter takes orders from every table, brings them to the kitchen together, and the chef cooks several dishes at once. That's batching. The chef is the GPU. Cooking several dishes at once costs barely more than cooking one, because the expensive part, getting the kitchen going, is shared.

Sam: And getting the kitchen going is reading the model weights.

Maya: Exactly. Now, the first version of batching people tried is called static batching. You wait until you've collected, say, eight requests, then you run them together as one batch until they're all finished.

Sam: Sounds reasonable.

Maya: It has a nasty problem. Requests finish at different times. One user asked for a one-sentence answer. Another asked for an essay. In static batching, the short one finishes early, but its slot in the batch just sits empty until the essay is done. And meanwhile, new users are waiting outside, unable to join, because the batch is "in progress."

Sam: Like a restaurant where nobody new can sit down until the slowest table has finished dessert.

Maya: Perfect analogy. So in 2022, a research paper called Orca introduced a better idea, which we now call continuous batching. Instead of treating the batch as one fixed group, the engine makes a decision at every single step. Every time it generates a token for everyone in the batch, it checks: has anyone finished? If so, remove them. Is anyone waiting? If there's room, add them.

Sam: So people are coming and going constantly.

Maya: Constantly, token by token. Tables get cleared and new guests sit down the moment there's space. The GPU stays full of useful work. Continuous batching is what made it practical to serve chatbots at scale, and every modern engine, vLLM, SGLang, and the rest, does it.

Sam: Okay, but there's got to be a catch. If I'm in a batch with thirty other people, am I slower than if I was alone?

Maya: Yes, a little. And this is the most important trade-off in the whole field. Each step now has to do the math for thirty people and read thirty people's KV caches. So each step takes a bit longer. From your point of view, the gap between your tokens grows. But the total output of the GPU, across everyone, goes way up.

Sam: So, for me personally, slightly slower. For the business, much more efficient.

Maya: Exactly. Let me put rough numbers on it, for a card like the L4. One user alone might get about twenty tokens a second. The GPU's total output is twenty tokens a second. Now with thirty-two users at once, maybe each user gets somewhere around ten to fifteen tokens a second. Slower for each person. But the GPU's total output might be three hundred, four hundred tokens a second, or more.

Sam: That's a fifteen or twenty times difference in total output, from the same hardware.

Maya: From the same hardware, for the same eighty cents an hour. That's the economics of the whole industry right there. And I want to stress, those are predictions based on the physics. We'll compare them to our actual benchmark later.

Sam: So when we built the benchmark, that's why it tests one user, then four, then sixteen, then thirty-two?

Maya: That's exactly why. We're tracing the curve. As you add users, total throughput rises, and each user's experience gets a bit worse. At some point, throughput stops rising, because you've run out of KV cache memory or compute, and requests start waiting in a queue. Then time to first token shoots up, because people are literally standing in line.

Sam: And that point where it bends, that's what you want to find.

Maya: That's the knee of the curve. It tells you the maximum number of users one GPU can handle while still giving an experience you're happy with. Then you can say things like "one L4 handles about this many concurrent users, so for a thousand users we need this many GPUs, and that costs this much a month." That's capacity planning, and it's what companies actually pay engineers to figure out.

Sam: Let me recap. Static batching groups requests and runs them together, but wastes slots when requests finish at different times. Continuous batching adds and removes requests at every token step, so the GPU stays full. Batching makes each user slightly slower but multiplies the GPU's total output, and finding where that trade-off bends tells you how many users one GPU can handle.

Maya: Great. Now, there's one problem we haven't solved. Continuous batching means requests are joining and leaving all the time, each with a KV cache that's growing at a different speed. How do you manage that memory without making a mess?

Sam: Let me guess. PagedAttention.

Maya: PagedAttention.
