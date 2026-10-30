Sam: Chapter seven. The three numbers. Maya, if I'm running an LLM in production, what do I actually watch?

Maya: Three numbers, above everything else. Time to first token, inter-token latency, and throughput. Let's take them one at a time, and I'll give you a feeling for each one, not just a definition.

Sam: Time to first token first.

Maya: Time to first token, or TTFT, is how long you wait after pressing enter before the very first word appears. It's the thing that makes an app feel fast or sluggish. Humans are very sensitive to it. If words start appearing in a couple of hundred milliseconds, it feels instant. If you stare at a blank screen for three seconds, it feels broken, even if the rest of the answer arrives quickly.

Sam: And we said it's mostly prefill.

Maya: Prefill, plus any time spent waiting in a queue, plus network time. So TTFT goes up when prompts get longer, and it shoots up when the server is overloaded and requests are waiting for a spot in the batch. That makes it a great early warning signal. When TTFT starts climbing, you're running out of capacity.

Sam: Next, inter-token latency.

Maya: Inter-token latency, or ITL, is the gap between each token once they start flowing. It's what makes the text stream smoothly or stutter. Reading speed for most people is around four or five words a second. So if you're producing tokens faster than about ten to fifteen a second, the reader can't really tell the difference. Below that, it starts to feel slow.

Sam: And that's set by decode, the memory-bound part.

Maya: Right. On our L4, for a single user, physics says roughly fifty milliseconds a token. As you add users to the batch, each step gets heavier, and ITL creeps up.

Sam: You'll sometimes hear a related term, time per output token, right?

Maya: Yes, people use TPOT and ITL almost interchangeably. Strictly speaking, ITL is each individual gap, and time per output token is the average over a whole response. Close enough for conversation.

Sam: And third, throughput.

Maya: Throughput is the total number of tokens the server produces per second, added up across all users. TTFT and ITL are about one user's experience. Throughput is about the business. Higher throughput means more users per GPU, which means a lower cost per user.

Sam: And the tension is that pushing throughput up makes the other two worse.

Maya: That's the whole game. Add more users to the batch, and throughput goes up, but TTFT and ITL get worse. Every serving team picks a target, something like "time to first token under one second and at least fifteen tokens a second per user, for ninety-nine percent of requests," and then squeezes as much throughput as possible while staying inside that target.

Sam: You said "ninety-nine percent of requests." That's the percentiles thing, right? P fifty, p ninety-nine?

Maya: Yes, and this is something that separates people who've actually run systems from people who've read about them. Never report just the average. Averages hide the pain.

Sam: Why?

Maya: Imagine ninety-nine requests take two hundred milliseconds and one takes twenty seconds. The average is about four hundred milliseconds. Looks fine. But one in every hundred users just waited twenty seconds and probably left. So we report percentiles. P fifty, the median, is the typical experience. Half of requests are faster, half are slower. P ninety means ninety percent of requests are faster than this. P ninety-nine means ninety-nine percent are faster. That's your worst-case-ish experience.

Sam: And our benchmark reports p fifty, p ninety, and p ninety-nine for both time to first token and inter-token latency.

Maya: It does. And the tail, the p ninety-nine, is often where you find the interesting problems. A big prefill landing in the middle of a batch. A request getting preempted because the KV cache filled up. A cold start.

Sam: There's another thing I want to understand. Our benchmark measures these numbers from my laptop, but vLLM also reports them itself, on the server. Why both?

Maya: Great question. They're measuring slightly different things. The server's numbers, which vLLM exposes on a metrics page that Prometheus collects and Grafana draws as charts, show what's happening inside the engine. How long requests waited in the queue. How full the KV cache is. How many requests are running versus waiting.

Sam: And the client numbers?

Maya: The client numbers include everything the user actually experiences. The network trip across the internet. The cloud provider's routing layer. Any cold start. The client is the truth about user experience. The server is where you go to find out why.

Sam: So if the client says time to first token is bad, but the server says it's fine...

Maya: The problem is in between. Network, load balancer, the cloud platform. If both say it's bad, look at the server dashboard. Is the queue growing? Is the KV cache full? That's the debugging loop.

Sam: Recap time. Time to first token is the wait before the first word, mostly prefill plus queueing, and it's what makes an app feel fast. Inter-token latency is the gap between words, set by decode, and it's what makes streaming feel smooth. Throughput is total tokens per second across all users, and it decides the cost. Adding users raises throughput but hurts the other two. Always report percentiles, not averages, because the tail is where users suffer.

Maya: Textbook. And you sounded like you meant it.
