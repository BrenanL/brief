// BAML Client Configurations for Brief
// These define the LLM providers available for description generation
//
// HOW TO CHANGE PROVIDERS:
// 1. Set the appropriate API key in your environment or .env file:
//    - OpenAI: OPENAI_API_KEY
//    - Anthropic: ANTHROPIC_API_KEY
//    - Google: GOOGLE_API_KEY
// 2. Modify the "Default" client at the bottom of this file to use your preferred provider
// 3. Run `baml-cli generate` from the brief directory to regenerate the client
//
// Example: To use Anthropic Claude instead of OpenAI:
//   client<llm> Default {
//     provider anthropic
//     options {
//       model "claude-3-5-haiku-20241022"
//       api_key env.ANTHROPIC_API_KEY
//       temperature 0.1
//     }
//   }

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

// =============================================================================
// DEFAULT CLIENT - Modify this to change your LLM provider
// =============================================================================
// Currently using: OpenAI GPT-4o-mini
// To switch providers, change 'provider' and 'model' below, then run:
//   baml-cli generate
//
// Provider options:
//   - openai (models: gpt-4o-mini, gpt-4o)
//   - anthropic (models: claude-3-5-haiku-20241022, claude-sonnet-4-20250514)
//   - google-ai (models: gemini-2.0-flash)
// =============================================================================
client<llm> Default {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
    temperature 0.1
  }
}
