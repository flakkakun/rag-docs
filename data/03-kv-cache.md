Sam: Chapter three. The KV cache. Maya, you promised math.

Maya: I did, but don't worry, it's multiplication. Let's work out how much memory the KV cache needs for a single token in our model, Qwen 2.5 seven billion.

Sam: Okay.

Maya: For each token, in each layer, we store a key and a value. Our model has twenty-eight layers. Now, one detail: Qwen uses something called grouped-query attention, where several query heads share the same keys and values. So instead of storing twenty-eight sets of keys and values per layer, it only stores four. Each of those is a list of a hundred and twenty-eight numbers, and each number takes two bytes.

Sam: So it's... two, for keys and values, times twenty-eight layers, times four heads, times a hundred and twenty-eight numbers, times two bytes.

Maya: Which comes out to about fifty-seven thousand bytes. Roughly fifty-six kilobytes. Per token.

Sam: Fifty-six kilobytes for one token. That doesn't sound like much.

Maya: It doesn't, until you multiply. A four-thousand-token conversation needs about two hundred and thirty megabytes of KV cache. And that's for one user. Now picture thirty users at once, each with a long conversation.

Sam: That's... several gigabytes.

Maya: Several gigabytes. And now let's look at the GPU we used. The Nvidia L4 has twenty-four gigabytes of memory. The model weights take about fifteen. We told vLLM it could use ninety percent of the card, so after the weights and some working space, you have something like six or seven gigabytes left for the KV cache.

Sam: And six gigabytes divided by fifty-six kilobytes per token is...

Maya: Roughly a hundred thousand tokens of cache, total, shared between everyone currently being served. That's your budget. If every user has a short chat, a few hundred tokens, you can fit hundreds of them. If every user is pasting in long documents, you might only fit twenty or thirty.

Sam: So the KV cache is literally the thing that decides how many people can use the GPU at the same time.

Maya: It's the main limit, yes. That's the sentence to remember. On a serving GPU, the weights are fixed. Whatever memory is left over becomes KV cache, and the KV cache decides how many users you can serve at once.

Sam: Now, by the way, this is why that grouped-query attention detail matters so much. If Qwen stored all twenty-eight heads' keys and values instead of four...

Maya: The cache would be seven times bigger, and you'd fit seven times fewer users. Model designers made that choice specifically to make serving cheaper. Many modern models do it.

Sam: Okay, so what happens when the cache fills up?

Maya: The engine has to make a choice. It can stop accepting new requests and make them wait in a queue. Or, if it's already mid-way through a lot of requests, it can pause some of them, throw away their cache, and recompute it later when there's room. vLLM calls that preemption. Either way, users feel it as waiting.

Sam: And I'm guessing that's something you'd want to watch on a dashboard.

Maya: Absolutely. In the project, the Grafana dashboard has a panel called "KV cache usage." It's a percentage. If it's sitting near a hundred percent and the "requests waiting" line is climbing, you've hit your memory limit. Your options are a bigger GPU, a smaller model, shorter contexts, or a cleverer way of using the memory.

Sam: And "a cleverer way of using the memory" is what vLLM is famous for.

Maya: That's PagedAttention, and we'll get there. But first, there's one more thing I need to explain, because it's going to completely change how you think about GPUs.

Sam: Which is?

Maya: When a GPU generates text, it's usually not limited by how fast it can do math. It's limited by how fast it can read memory.

Sam: That sounds backwards. Aren't GPUs famous for doing math really fast?

Maya: They are. And that's exactly why it's surprising. Let's talk about it.

Sam: Quick recap before we do. KV cache: the stored keys and values for every token the model has already seen, so it doesn't have to recompute them. About fifty-six kilobytes per token on our model. It grows with conversation length and with the number of users, and it's what limits how many people you can serve at once.

Maya: Perfect. That's an interview answer right there.
