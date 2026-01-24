# POST 4 - MULTI-AGENT ORCHESTRATION

Here's where it gets interesting.

You can spawn **independent Claude instances** that run in parallel:

```
agent_spawn("Research quantum computing", type="researcher")
agent_spawn("Write the technical spec", type="writer")
agent_spawn("Review for errors", type="analyst")
```

They work simultaneously.
They can spawn OTHER agents.
They report back when done.

And then there's the **Socratic Council**...
