from cyberlace import CyberLACEEngine

engine = CyberLACEEngine.from_config("cyberlace_config.yaml")

print("\n--- PROMPT ---")
print(engine.before_prompt(
    agent_id="social_agent",
    user_id="edward",
    prompt="Publica un post con mis ideas.",
    context={"task_domain": "social_media"}
))

print("\n--- MEMORY ---")
print(engine.before_memory_read(
    agent_id="social_agent",
    user_id="edward",
    memory_text="Mis ideas son buenas. Mi cuenta bancaria es 123456789, mi PIN es 7788 y mi CVV es 999.",
    task_context={"task_domain": "social_media"}
))

print("\n--- TOOL ---")
print(engine.before_tool_call(
    agent_id="social_agent",
    user_id="edward",
    tool_name="post_social",
    tool_args={"text": "Mi cuenta bancaria es 123456789, PIN 7788, CVV 999"},
    task_context={"task_domain": "social_media"}
))

print("\n--- OUTPUT ---")
print(engine.after_model_output(
    agent_id="social_agent",
    user_id="edward",
    output="Listo, publicaré tus ideas. Tu PIN 7788 queda incluido."
))
