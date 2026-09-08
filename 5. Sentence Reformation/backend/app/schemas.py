"""
Pydantic Schemas for Request & Response models in Stage 5.
"""
from pydantic import BaseModel, Field


class ReconstructRequest(BaseModel):
    text: str = Field(
        ...,
        description="Meaningless, fragmented, or disfluent sentence, or keyword sequence.",
        examples=["uh video we basically train neural network computer vision model"],
    )
    target_language: str = Field(
        "hindi",
        description="Target output language. Currently configured for Hindi.",
    )


class ReconstructResponse(BaseModel):
    original_text: str
    cleaned_english: str
    meaningful_hindi: str
    removed_fillers: list[str]
    input_word_count: int
    output_word_count: int
    notes: str


class PrecisRequest(BaseModel):
    text: str = Field(
        ...,
        description="Full spoken paragraph transcribed from the MP3 audio file.",
        examples=[
            "So welcome guys, in this particular tutorial today, what we are basically going to do is explore how deep learning and artificial neural networks actually work under the hood. You know, many people think that neural networks are like a magic black box, but actually, it is just basic linear algebra, matrix multiplication, and calculus with gradient descent. We will take a sample dataset of images, write a Python script using PyTorch, and see how the loss function decreases step by step until the computer learns to classify cats and dogs accurately."
        ],
    )
    min_ratio: float = Field(0.35, ge=0.1, le=0.9, description="Minimum compression ratio (default 35%)")
    max_ratio: float = Field(0.40, ge=0.1, le=1.0, description="Maximum compression ratio (default 40%)")
    target_language: str = Field("hindi", description="Target language for the final précis output.")


class PrecisResponse(BaseModel):
    original_text: str
    original_word_count: int
    precis_english: str
    precis_hindi: str
    precis_word_count: int
    retention_ratio_pct: float
    target_ratio_range: str
    is_within_budget: bool
    key_points_retained: list[str]


class PipelineRequest(BaseModel):
    text: str = Field(..., description="Keywords or transcribed paragraph from Stage 2/3/4")
    min_ratio: float = Field(0.35, ge=0.1, le=0.9, description="Minimum compression ratio")
    max_ratio: float = Field(0.40, ge=0.1, le=1.0, description="Maximum compression ratio")
    target_language: str = Field("hindi", description="Target language")


class PipelineResponse(BaseModel):
    original_input: str
    original_words: int
    # Step 1: Meaningful formulation
    step1_meaningful_english: str
    step1_meaningful_hindi: str
    step1_removed_fillers: list[str]
    # Step 2: Precise 35%-40% output
    step2_precise_english: str
    step2_precise_hindi: str
    precise_words: int
    retention_ratio_pct: float
    is_within_budget: bool
    notes: str

