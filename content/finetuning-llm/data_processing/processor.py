import json
import re

from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer


class Processor:
    """Processes conversation data into training format."""

    DEFAULT_SYSTEM_PROMPT = (
        "Summarize this conversation between a human and AI assistant, "
        "capturing key points and maintaining context."
    )
    COLUMNS_TO_REMOVE = [
        "original dialog id",
        "new dialog id",
        "dialog index",
        "original dialog info",
        "log",
        "prompt",
    ]

    def __init__(
        self,
        tokenizer: AutoTokenizer,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        seed: int = 42,
    ):
        """Initialize the conversation processor.

        Args:
            tokenizer: Tokenizer for text processing
            system_prompt: Instruction prompt for summarization
            seed: Random seed for reproducibility
        """
        self.system_prompt = system_prompt
        self.seed = seed
        self.tokenizer = tokenizer

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing unwanted patterns.

        Args:
            text: Input text to clean

        Returns:
            Cleaned text with URLs, mentions, and extra whitespace removed
        """
        text = re.sub(r"http\S+|@[^\s]+|\^[^ ]+", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def format_conversation(self, log: list[dict]) -> str:
        """Format conversation log into structured text.

        Args:
            log: List of conversation turns

        Returns:
            Formatted conversation string
        """
        return "\n".join(
            f"user: {self.clean_text(turn['user utterance'])}\n"
            f"agent: {self.clean_text(turn['system response'])}"
            for turn in log
        )

    @staticmethod
    def extract_summary(original_info: str) -> str:
        """Extract summary from original dialog info.

        Args:
            original_info: JSON string containing original dialog info

        Returns:
            Extracted summary text
        """
        summaries = json.loads(original_info).get("summaries", {})
        abstractive = summaries.get("abstractive_summaries", [])
        return " ".join(abstractive[0]) if abstractive else ""

    def generate_prompt(self, conversation: str, summary: str | None = None) -> str:
        """Generate training prompt with optional summary.

        Args:
            conversation: Formatted conversation text
            summary: Optional summary text

        Returns:
            Complete training prompt
        """
        response_part = f"### Response:\n{summary}" if summary else "### Response:\n"
        return (
            f"### Instruction: {self.system_prompt}\n\n"
            f"### Input:\n{conversation}\n\n"
            f"{response_part}"
        )

    def process_sample(self, sample: dict) -> dict[str, str]:
        """Process single sample into training format.

        Args:
            sample: Input data sample

        Returns:
            Processed sample with conversation, summary and formatted text
        """
        conversation = self.format_conversation(sample.get("log", []))
        summary = self.extract_summary(sample["original dialog info"])
        return {
            "conversation": conversation,
            "summary": summary,
            "text": self.generate_prompt(
                conversation, summary if summary.strip() else None
            ),
        }

    def process_dataset(
        self, dataset: Dataset | DatasetDict, tokenize: bool = False
    ) -> Dataset | DatasetDict:
        """Process dataset with optional tokenization.

        Args:
            dataset: Input dataset to process
            tokenize: Whether to tokenize the text

        Returns:
            Processed dataset
        """

        def _process(data: Dataset) -> Dataset:
            data = (
                data.shuffle(seed=self.seed)
                .map(self.process_sample)
                .remove_columns(self.COLUMNS_TO_REMOVE)
            )
            if tokenize and self.tokenizer:
                data = data.map(lambda x: self.tokenizer(x["text"]))
            return data

        if isinstance(dataset, DatasetDict):
            return DatasetDict({k: _process(v) for k, v in dataset.items()})
        return _process(dataset)
