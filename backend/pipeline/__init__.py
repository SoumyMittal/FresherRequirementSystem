"""Standalone inference pipeline. No FastAPI, OCR, UI, or network dependencies."""
from .pipeline import RecruitmentPipeline

__all__ = ['RecruitmentPipeline']
