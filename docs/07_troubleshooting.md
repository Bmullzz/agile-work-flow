# Troubleshooting

The current troubleshooting guide is maintained at [troubleshooting.md](troubleshooting.md).

Common backend-specific issues:

- OpenAI API mode requires `OPENAI_API_KEY`.
- Manual ChatGPT mode requires a fresh response file under `99-meta/manual-responses/`.
- Codex mode validates that task target paths match workflow output paths.
- Mock mode is deterministic and should not require network access or credentials.

Common validation failures:

- missing H1 heading
- missing required sections
- chat preamble in generated Markdown
- full-document fenced code block
- unresolved placeholders such as `{{APP_IDEA}}`

Check logs at:

```text
output/my-project/logs/workflow.log
```
