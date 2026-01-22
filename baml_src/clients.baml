// BAML Client Configurations for Brief
// These define the LLM providers available for description generation

// Generator config - outputs to brief/baml_client/
// BAML always creates a "baml_client" folder, so output_dir=".." creates brief/baml_client/
generator target {
  output_type "python/pydantic"
  output_dir ".."
  version "0.217.0"
}

// OpenAI clients
client<llm> GPT5Mini {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
    temperature 0.1
  }
}

client<llm> GPT4o {
  provider openai
  options {
    model "gpt-4o"
    api_key env.OPENAI_API_KEY
    temperature 0.1
  }
}

// Anthropic clients
client<llm> ClaudeSonnet {
  provider anthropic
  options {
    model "claude-sonnet-4-20250514"
    api_key env.ANTHROPIC_API_KEY
    temperature 0.1
  }
}

client<llm> ClaudeHaiku {
  provider anthropic
  options {
    model "claude-3-5-haiku-20241022"
    api_key env.ANTHROPIC_API_KEY
    temperature 0.1
  }
}

// Google clients (for future use)
client<llm> GeminiFlash {
  provider google-ai
  options {
    model "gemini-2.0-flash"
    api_key env.GOOGLE_API_KEY
    temperature 0.1
  }
}

// Default client - change this to switch the default model
client<llm> Default {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
    temperature 0.1
  }
}
