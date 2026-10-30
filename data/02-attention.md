Sam: Chapter two. Attention. Maya, people say "attention is all you need." What does that even mean?

Maya: It's the title of the 2017 research paper that introduced the transformer, the design behind basically every modern language model. And attention is the core trick inside it. So let's build it up from a simple example.

Sam: Go for it.

Maya: Take this sentence. "The cat sat on the mat because it was tired." What does "it" refer to?

Sam: The cat. Mats don't get tired.

Maya: Right. You figured that out instantly, because you looked back at the earlier words and decided which one mattered for understanding "it." That looking back, deciding what's relevant, is attention. Every time the model processes a token, it looks back at every earlier token and decides how much each one matters right now.

Sam: Okay, but a computer can't just "decide." How does it actually do that?

Maya: This is where queries, keys, and values come in. And I promise, it's simpler than it sounds. Think of a library.

Sam: A library. Okay.

Maya: You walk in with a question in your head. That's your query. "I'm looking for something about tired animals." Every book on the shelf has a label on its spine describing what it's about. That's the key. And inside each book is the actual content. That's the value.

Sam: So the query is what I'm searching for, the key is the label, and the value is what's inside.

Maya: Exactly. Now, inside the model, every token gets turned into three lists of numbers: a query, a key, and a value. When the model is working on the word "it," it takes the query for "it" and compares it against the key of every earlier word. "The," "cat," "sat," "on," "the," "mat." Each comparison gives a score. How relevant is this word to me?

Sam: And "cat" scores high.

Maya: "Cat" scores high, "mat" scores lower, "the" scores very low. Then the model takes the values of all those earlier words and blends them together, weighted by the scores. So the new understanding of "it" is mostly made of "cat," with a little bit of everything else mixed in.

Sam: That's actually elegant. It's a weighted average where the weights come from how well the query matches each key.

Maya: That's precisely what it is. And it happens over and over. A model like Qwen 2.5 seven billion has twenty-eight layers stacked on top of each other, and attention happens in every single one. Early layers might pick up simple things like grammar. Deeper layers pick up meaning, tone, which facts are relevant. Each layer refines the understanding a bit more.

Sam: And there's more than one attention per layer, right? I've heard "multi-head attention."

Maya: Yes. Each layer has several attention heads running side by side, each with its own queries, keys, and values. You can think of them as different readers looking for different things. One head might track who's doing what. Another might track which words go together grammatically. Qwen 2.5 seven billion has twenty-eight query heads per layer.

Sam: Okay, so here's what I want to understand. Why does this make generating text slow?

Maya: Good, this is the bridge to the next chapter. Remember, the model writes one token at a time. Every new token needs to look back at every earlier token. And to look back, it needs the keys and values of all those earlier tokens.

Sam: So for token two hundred, it needs the keys and values of the previous one hundred and ninety-nine tokens.

Maya: In every layer. Now, here's the key observation. Once a token has been processed, its keys and values never change. The key for "cat" at position two is exactly the same whether you're now generating token ten or token two hundred.

Sam: So you could just... save them?

Maya: You could just save them. And that's exactly what every serious inference engine does. Instead of recalculating the keys and values for the whole conversation every time you generate a new token, you calculate them once, store them, and reuse them. The thing where you store them has a name.

Sam: The KV cache.

Maya: The KV cache. K for keys, V for values. And it is, without exaggeration, the single most important thing to understand about serving language models. It's why memory matters so much, it's what vLLM was invented to manage, and it's what decides how many users you can fit on one GPU.

Sam: Before we go there, let me try to summarize attention in one breath, the way I'd say it in an interview.

Maya: Go.

Sam: Attention is how a model decides which earlier words matter for the current word. Each token gets a query, a key, and a value. The query is compared with every earlier key to get relevance scores, and the output is a weighted mix of the earlier values.

Maya: That's a genuinely good answer. If you add one more sentence, "and since earlier keys and values never change, inference engines cache them," you've just set up the next question perfectly.

Sam: Which is: how big does that cache get?

Maya: Let's do the math. It's surprising.
