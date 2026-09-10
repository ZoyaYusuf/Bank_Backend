from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.interest_service import calculate_active_loan, calculate_historical_loan

app = FastAPI(title='ARRA Interest Calculator API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://bank-frontend-kappa.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


class LoanRequest(BaseModel):
    principal: float = Field(..., gt=0)
    reference_rate: str = Field(default='SOFR')
    spread: float = Field(default=2.0, ge=0)
    start_date: str
    end_date: str | None = None
    day_count: str = Field(default='ACT/360')
    as_of_date: str | None = None


@app.get('/health')
def health_check() -> dict:
    return {'status': 'ok'}


@app.post('/api/historical-loan')
def calculate_historical(request: LoanRequest):
    if not request.end_date:
        raise HTTPException(status_code=400, detail='Historical calculations require an end date.')
    try:
        return calculate_historical_loan(
            principal=request.principal,
            reference_rate=request.reference_rate,
            spread=request.spread,
            start_date=request.start_date,
            end_date=request.end_date,
            day_count=request.day_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - broad fallback for frontend diagnostics
        raise HTTPException(status_code=500, detail=f'Unexpected historical calculation error: {exc}') from exc


@app.post('/api/active-loan')
def calculate_active(request: LoanRequest):
    try:
        return calculate_active_loan(
            principal=request.principal,
            reference_rate=request.reference_rate,
            spread=request.spread,
            start_date=request.start_date,
            as_of_date=request.as_of_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - broad fallback for frontend diagnostics
        raise HTTPException(status_code=500, detail=f'Unexpected active calculation error: {exc}') from exc


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
