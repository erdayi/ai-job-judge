from __future__ import annotations

import csv
import io
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models import (
    ApplicationKitRequest,
    ApplicationKitResponse,
    CombinedAnalyzeRequest,
    CombinedAnalyzeResponse,
    JobsExtractResponse,
    JobsMatchRequest,
    JobsMatchResponse,
    PageAnalyzeResponse,
    PageSnapshot,
    RankRequest,
    RankResponse,
    ResumeRulesRequest,
    ResumeRulesResponse,
    ResumeUploadResponse,
)
from app.services.application_kit import generate_application_kit
from app.services.job_extraction import extract_jobs, extract_jobs_with_fallback
from app.services.matcher import match_jobs
from app.services.page_analysis import analyze_page
from app.services.ranker import rank_jobs
from app.services.resume import extract_resume_text, generate_resume_rules
from app.storage.store import JsonStore

app = FastAPI(title="AI Job Judge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*|http://127\.0\.0\.1:\d+|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = JsonStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile | None = File(default=None), text: str | None = Form(default=None)) -> ResumeUploadResponse:
    resume_text = await extract_resume_text(file, text)
    if not resume_text:
        raise HTTPException(status_code=400, detail="请上传简历文件或填写简历文本")
    resume_id = store.save_resume(resume_text)
    return ResumeUploadResponse(
        resume_id=resume_id,
        text_length=len(resume_text),
        preview=resume_text[:300],
        extracted_text=resume_text,
    )


@app.get("/resume/{resume_id}", response_model=ResumeUploadResponse)
def get_resume(resume_id: str) -> ResumeUploadResponse:
    resume_text = store.get_resume(resume_id)
    if not resume_text:
        raise HTTPException(status_code=404, detail="未找到简历")
    return ResumeUploadResponse(
        resume_id=resume_id,
        text_length=len(resume_text),
        preview=resume_text[:300],
        extracted_text=resume_text,
    )


@app.post("/resume/rules", response_model=ResumeRulesResponse)
async def resume_rules(request: ResumeRulesRequest) -> ResumeRulesResponse:
    resume_text = request.resume_text or (store.get_resume(request.resume_id) if request.resume_id else None)
    if not resume_text:
        raise HTTPException(status_code=404, detail="未找到简历，请先上传简历")
    resume_id = request.resume_id or store.save_resume(resume_text)
    profile, raw_rules, source = await generate_resume_rules(resume_text)
    store.save_rules(resume_id, profile, raw_rules, source)
    return ResumeRulesResponse(resume_id=resume_id, profile=profile, raw_rules=raw_rules, source=source)


@app.post("/page/analyze", response_model=PageAnalyzeResponse)
def page_analyze(snapshot: PageSnapshot) -> PageAnalyzeResponse:
    return analyze_page(snapshot)


@app.post("/jobs/extract", response_model=JobsExtractResponse)
async def jobs_extract(snapshot: PageSnapshot) -> JobsExtractResponse:
    return await extract_jobs_with_fallback(snapshot)


@app.post("/jobs/match", response_model=JobsMatchResponse)
def jobs_match(request: JobsMatchRequest) -> JobsMatchResponse:
    profile = request.profile or (store.get_profile(request.resume_id) if request.resume_id else None) or store.latest_profile()
    matches = match_jobs(request.jobs, profile, request.max_candidates)
    return JobsMatchResponse(matches=matches, total=len(request.jobs), kept=len(matches))


@app.post("/jobs/rank", response_model=RankResponse)
async def jobs_rank(request: RankRequest) -> RankResponse:
    profile = request.profile or (store.get_profile(request.resume_id) if request.resume_id else None) or store.latest_profile()
    resume_text = store.get_resume(request.resume_id) if request.resume_id else None
    response = await rank_jobs(request.matches, profile, request.top_n, resume_text)
    store.save_results(str(uuid.uuid4()), response.model_dump())
    return response


@app.post("/jobs/application-kit", response_model=ApplicationKitResponse)
async def jobs_application_kit(request: ApplicationKitRequest) -> ApplicationKitResponse:
    profile = request.profile or (store.get_profile(request.resume_id) if request.resume_id else None) or store.latest_profile()
    resume_text = store.get_resume(request.resume_id) if request.resume_id else None
    return await generate_application_kit(request, profile, resume_text)


@app.post("/scan/analyze", response_model=CombinedAnalyzeResponse)
async def scan_analyze(request: CombinedAnalyzeRequest) -> CombinedAnalyzeResponse:
    page = analyze_page(request.snapshot)
    extracted = await extract_jobs_with_fallback(request.snapshot)
    profile = request.profile or (store.get_profile(request.resume_id) if request.resume_id else None) or store.latest_profile()
    resume_text = store.get_resume(request.resume_id) if request.resume_id else None
    matches = match_jobs(extracted.jobs, profile, request.max_candidates)
    matched = JobsMatchResponse(matches=matches, total=len(extracted.jobs), kept=len(matches))
    ranked = await rank_jobs(matches, profile, request.top_n, resume_text)
    store.save_results(str(uuid.uuid4()), ranked.model_dump())
    return CombinedAnalyzeResponse(page=page, extracted=extracted, matched=matched, ranked=ranked)


@app.get("/results/export")
def export_results(format: str = "json"):
    data = store.export_results()
    if format.lower() != "csv":
        return data

    rows = []
    for payload in data.values():
        for item in payload.get("results", []):
            rows.append(
                {
                    "rank": item.get("rank"),
                    "score": item.get("score"),
                    "decision": item.get("decision"),
                    "title": item.get("title"),
                    "company": item.get("company"),
                    "job_url": item.get("job_url"),
                    "reasons": " | ".join(item.get("reasons", [])),
                    "risks": " | ".join(item.get("risks", [])),
                }
            )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["rank", "score", "decision", "title", "company", "job_url", "reasons", "risks"])
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=job-results.csv"})
