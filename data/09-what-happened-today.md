Sam: Chapter nine. What actually happened when we deployed it. Maya, walk us through the project from the beginning.

Maya: The goal was simple to say: take an open-source model, serve it on a real GPU in the cloud, and measure time to first token, inter-token latency, and throughput. Then put it all on GitHub as proof that you can do it, not just talk about it.

Sam: And the first problem was hardware.

Maya: Right. The laptop we were working on is an Apple Mac with an M4 chip and sixteen gigabytes of memory. A lovely machine, but vLLM is built for Nvidia GPUs. So we needed to rent one.

Sam: And we picked Modal.

Maya: Modal is a cloud platform where you write normal Python, add a few lines describing the hardware you want, and it runs your code on their GPUs. You pay by the second, only while your code is running, and the free plan includes thirty dollars of credit a month. That's around thirty-seven hours on an L4, which is far more than this project needs.

Sam: What does the setup actually look like?

Maya: It's one Python file. It describes a container image with vLLM installed. It attaches two storage volumes, one to cache the model weights so they only download once, and one for vLLM's compiled files. It asks for one L4 GPU. And then it runs the command "vllm serve," which starts an OpenAI-compatible API. That means any code that knows how to talk to OpenAI can talk to our server instead, just by changing the address.

Sam: And there were some safety settings.

Maya: Three important ones, mostly to protect the free credit. First, maximum one container, so a sudden flood of traffic can never spin up ten GPUs. Second, scale down after three minutes of no traffic, so the GPU turns itself off when nobody's using it. Third, an API key, so random people on the internet who stumble across the address can't use our model and burn our credits.

Sam: And then we pressed deploy.

Maya: And then we hit the first real-world wall. Modal said, essentially, "please add a payment method to use L4 GPUs." Even with free credits, GPU access needs a card on file. That's a normal anti-abuse measure. Lesson one: check account requirements before your demo day.

Sam: We also caught a sneaky version problem in that first build.

Maya: We did. The build logs showed it was installing a brand-new version of the Hugging Face library that the version of vLLM we'd chosen didn't expect. Software libraries evolve constantly, and a new major version can break older code that depends on it. So we pinned the versions, explicitly telling the installer "stay below version five" and "stay below version one." Lesson two: in production, pin your versions. "Latest" is not a version.

Sam: Then the card got added, and the deploy succeeded.

Maya: In under a minute. We got a public web address for the server. Then we ran the benchmark, and hit wall number two.

Sam: The redirect.

Maya: The redirect. The very first request has to wait for a cold start. Modal has to find a GPU, start the container, download fifteen gigabytes of model weights, load them onto the GPU, and let vLLM warm up. That can take several minutes. And Modal has a rule: if a web request takes longer than about two and a half minutes, instead of keeping the connection open forever, it replies with a redirect, basically saying "still working, check back at this address."

Sam: And our benchmark script treated that as an error and crashed.

Maya: Right. The fix was a pattern you'll use forever: health checks. vLLM has a health endpoint that just answers "I'm okay" once the model is loaded. So now the benchmark first asks "are you healthy?" every five seconds, following any redirects, and only starts the real test once the answer is yes. Lesson three: never assume a server is ready just because it's deployed. Check.

Sam: And then wall number three.

Maya: The cloud ran out of GPUs. The logs said the function was waiting to be scheduled on an L4 worker, and that Modal was working on getting more capacity. Cloud GPUs are a shared, limited resource, and sometimes everyone wants the same card at the same time.

Sam: What can you do about that?

Maya: A few things. You can wait, which usually works within minutes. You can give the platform a list of acceptable GPUs, so if the L4s are busy it falls back to something similar, like an A10, which has the same twenty-four gigabytes. Or, for a real business, you reserve capacity in advance. We chose to wait, so that the first set of results all came from the same kind of GPU and stayed comparable. Lesson four: GPU capacity is not guaranteed, so have a fallback plan.

Sam: And none of that waiting cost money?

Maya: Waiting in the queue doesn't bill. You pay from when your container is actually running. And because we set it to scale to zero, it turns itself off a few minutes after the benchmark ends.

Sam: Now, the monitoring side. We built a dashboard too.

Maya: Yes. vLLM publishes a metrics page in a standard format that a tool called Prometheus understands. Prometheus collects those numbers every few seconds and stores them. Grafana turns them into live charts. We set up a dashboard with six panels: time to first token, inter-token latency, throughput, requests running and waiting, KV cache usage, and end-to-end latency. Both tools run for free on the laptop, using Docker.

Sam: But there was a gotcha there too.

Maya: A really subtle one. Every time Prometheus collects metrics, that's a web request to the server. On Modal, any request counts as activity. So if Prometheus is checking every five seconds, the server never sees three quiet minutes, and the GPU never turns off. You'd quietly burn credits all night.

Sam: So the rule is...

Maya: Only run the dashboard during a benchmark, then switch it off. Lesson five: monitoring has a cost too, and you have to understand how your platform decides when you're idle.

Sam: Five lessons from one afternoon. That's actually a great story to tell in an interview.

Maya: It's a better story than if everything had worked the first time. Interviewers love hearing what broke and how you diagnosed it, because that's what the job really is.
