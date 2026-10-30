Sam: Welcome to Under the Hood. I'm Sam, and here's my confession: I use AI chatbots every day, and until recently I had no idea what actually happens between me pressing enter and words showing up on screen.

Maya: And I'm Maya. I'm an engineer who works on exactly that gap. Over the next hour we're going to open the hood all the way. By the end, you'll be able to explain how a large language model gets served to thousands of people at once, why it's fast or slow, and what it costs.

Sam: And we're going to do it around a real project. One we actually built and deployed today: an open-source model, running on a rented GPU in the cloud, with a benchmark that measures exactly how fast it is.

Maya: Which, spoiler, did not go perfectly. We'll get to that. Real deployments never go perfectly, and the stumbles are where you learn the most.

Sam: Okay, let's start at the very beginning. I type, "Explain why the sky is blue." I press enter. What happens?

Maya: First, your text never reaches the model as text. Models don't read letters or words. They read tokens.

Sam: Tokens. I've heard that word a hundred times. What is a token, really?

Maya: A token is a chunk of text, usually a piece of a word. Common words like "the" or "sky" are one token each. A longer or rarer word, like "photosynthesis," might get split into three or four pieces. A good rule of thumb in English is that one token is about three quarters of a word. So a hundred words is roughly a hundred and thirty tokens.

Sam: Why not just use whole words?

Maya: Because there are too many words, and new ones appear all the time. Names, typos, code, emoji. With sub-word pieces, the model gets a fixed vocabulary, usually somewhere between fifty thousand and a hundred and fifty thousand tokens, and it can still spell out anything by combining pieces. Each token gets turned into an ID number, and that list of numbers is what the model actually sees.

Sam: So "Explain why the sky is blue" becomes something like seven numbers.

Maya: Exactly. Now those numbers go into the model. And here's the second big idea. The model is, at its heart, a giant file of numbers called weights, or parameters.

Sam: In our project, we used a model called Qwen 2.5, the seven billion parameter version.

Maya: Right. Seven billion numbers. Each one is stored using two bytes, so the whole model is about fifteen gigabytes. That fifteen gigabyte file is, in a very real sense, everything the model knows. Grammar, facts, how to write code, how to be polite. All of it is squeezed into the precise values of those seven billion numbers, learned during training.

Sam: That's wild. Fifteen gigabytes. That's smaller than some video games.

Maya: It is. And here's the third idea, the one that drives this entire episode. The model does not write your answer all at once. It writes it one token at a time.

Sam: One at a time? Even though it looks like it's streaming out fast?

Maya: One at a time. The model looks at everything so far, your question, and predicts the single most likely next token. Say it picks "The." Then it adds "The" to the text and runs again, looking at your question plus "The," and predicts the next token. Maybe "sky." Then again. And again. Every single token in the answer is a full trip through the model.

Sam: So a two hundred token answer means running the model two hundred times.

Maya: Two hundred times, in a row, and each step has to wait for the one before it, because you can't predict word five until you know word four. That's called autoregressive generation, and it's the root of almost every performance problem we'll talk about.

Sam: Okay, so where does this happen? On my laptop?

Maya: For a model this size, usually not. It happens on a GPU, a graphics card, sitting in a data center. And that brings us to the piece of software in the title of our project: vLLM.

Sam: And I'll admit, when I first saw "vLLM," I assumed it was a type of model. Like a "virtual LLM."

Maya: Super common mix-up. vLLM is not a model. It's an inference engine. Inference just means using a trained model to produce answers, as opposed to training it. vLLM is the software that loads those fifteen gigabytes of weights onto the GPU, accepts requests from users over the internet, runs the token-by-token loop, and streams the results back. It's the bridge between a model file and a working API.

Sam: So if the model is the brain, vLLM is the body that lets the brain talk to the world.

Maya: I like that. And the reason vLLM matters so much is that a naive version of that bridge is incredibly wasteful. You could write a simple program that loads the model and answers one user at a time. It would work. It would also leave your very expensive GPU sitting mostly idle, and the second user would wait in line behind the first.

Sam: And GPUs are not cheap.

Maya: Not at all. The one we rented today, an Nvidia L4, costs about eighty cents an hour. The big ones, like an H100, can cost three or four dollars an hour. If you're a company serving millions of users, the difference between using that GPU well and using it badly is the difference between a business that works and one that burns money.

Sam: So that's our journey for the next hour. We're going to figure out what actually happens inside that token-by-token loop, why it's slow, and the clever tricks that make it fast.

Maya: We'll cover attention, which is how the model decides what to focus on. The KV cache, which is the model's short-term memory. Why GPUs are actually limited by memory speed, not math. Batching, which is how one GPU serves dozens of people at once. PagedAttention, the big idea behind vLLM. And then the three numbers every serving engineer lives by: time to first token, inter-token latency, and throughput.

Sam: And then we'll tell you what happened when we tried this for real.

Maya: Including the part where the cloud ran out of GPUs.

Sam: Let's go.
