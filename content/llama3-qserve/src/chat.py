import argparse
from typing import List, Tuple
import random

import datasets

import qserve.utils.constants
from qserve import EngineArgs, LLMEngine, SamplingParams
from qserve.conversation import get_conv_template_name, get_conv_template

max_seq_len = qserve.utils.constants.max_seq_len

random.seed(484)

import re

def extract_llama3_assistant(text):
    # Create a regex pattern to capture text between '>' and '<'
    pattern = re.compile(r'<|end_header_id|>([^<]+)<|eot_id|>')
    
    # Find all non-overlapping matches in the text
    matches = pattern.findall(text)
    
    # Strip whitespace at the start and end of each match
    cleaned_matches = [match.strip() for match in matches]
    assistant_response = [x for x in cleaned_matches if len(x) > 0 ][-1]
    return assistant_response


def initialize_engine(args: argparse.Namespace) -> LLMEngine:
    """Initialize the LLMEngine from the command line arguments."""
    engine_args = EngineArgs.from_cli_args(args)
    return LLMEngine.from_engine_args(engine_args)


def main(args: argparse.Namespace):
    """Main function that sets up and runs the prompt processing."""
    engine = initialize_engine(args)
    conv_t = get_conv_template_name(args.model)
    conv = get_conv_template(conv_t)
    sampling_params = SamplingParams(temperature=0.7, top_p=1.0, stop_token_ids=[128001, 128009], max_tokens=1024)
    eject = False
    while not eject:
        if not engine.has_unfinished_requests():
            user_input = input("User: ")
            if user_input.lower() == 'exit':
                print("Exiting the conversation.")
                eject = True
            else:
                conv.append_message(conv.roles[0], user_input)
                conv.append_message(conv.roles[1], "")
                prompt = conv.get_prompt()
                engine.add_request(0, prompt, sampling_params)
        if eject:
            break
        request_outputs = engine.step()
        for request_output in request_outputs:
            if request_output["finished"]:
                response = request_output["text"]
                ext_response = extract_llama3_assistant(response)
                print(f"Assistant: {ext_response}")
                conv.update_last_message(ext_response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Demo on using the LLMEngine class directly"
    )
    parser = EngineArgs.add_cli_args(parser)
    args = parser.parse_args()
    main(args)
