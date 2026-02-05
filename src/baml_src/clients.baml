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

// Generator config - outputs to src/baml_client/ (sibling directory)
generator target {
  output_type "python/pydantic"
  output_dir ".."
  version "0.218.1"
}

// =============================================================================
// OpenAI Clients
// =============================================================================

client<llm> GPT4oMini {
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

// Note: gpt-5-mini only supports temperature=1.0
client<llm> GPT5Mini {
  provider openai
  options {
    model "gpt-5-mini"
    api_key env.OPENAI_API_KEY
  }
}

// =============================================================================
// Anthropic Clients
// =============================================================================

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

// =============================================================================
// Google Gemini Clients
// Note: For google-ai, temperature goes in generationConfig, not at top level
// =============================================================================

client<llm> Gemini20Flash {
  provider google-ai
  options {
    model "gemini-2.0-flash"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}

client<llm> Gemini20FlashLite {
  provider google-ai
  options {
    model "gemini-2.0-flash-lite"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}

client<llm> Gemini25FlashLite {
  provider google-ai
  options {
    model "gemini-2.5-flash-lite"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}

client<llm> Gemini25Flash {
  provider google-ai
  options {
    model "gemini-2.5-flash"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}

client<llm> Gemini3FlashPreview {
  provider google-ai
  options {
    model "gemini-3-flash-preview"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}

// =============================================================================
// DEFAULT CLIENT - Used when no specific model is requested
// =============================================================================
// This is the fallback client. Runtime model selection overrides this.
client<llm> Default {
  provider google-ai
  options {
    model "gemini-2.5-flash"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      temperature 0.1
    }
  }
}
