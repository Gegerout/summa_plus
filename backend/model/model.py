from unsloth import FastLanguageModel

max_seq_length = 2048
dtype = None
load_in_4bit = True

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="llama_model",
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)


def generate_summ(input_text):
    alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

  ### Instruction:
  Summarize this dialogue and try to keep facts:

  ### Input:
  {}

  ### Response:
  {}"""

    inputs = tokenizer(
        [
            alpaca_prompt.format(
                input_text,
                "",
            )
        ], return_tensors="pt").to("cuda")

    tokenized_output = model.generate(**inputs, use_cache=True)

    decoded_output = tokenizer.batch_decode(tokenized_output, skip_special_tokens=True)

    decoded_text = ''.join(decoded_output)

    start_index = decoded_text.find('### Response:') + len('### Response:')  # Adjust start index
    end_index = decoded_text.find('### Instruction:', start_index)

    response = decoded_text[start_index:end_index].strip()

    response = response.rstrip('<|end_of_text|>').strip()

    return response
