import asyncio
from app.ml.evaluation.hybrid_scorer import evaluate_answer

async def main():
    print("Testing evaluation...")
    res = await evaluate_answer(
        transcript="We use straight line depreciation for our assets. We estimate the salvage value at the end of useful life and divide the depreciable base by the number of years.",
        job_title="Senior Accountant",
        job_description="Responsible for asset management and general ledger."
    )
    print("Result:")
    import json
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
