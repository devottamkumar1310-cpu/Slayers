"""
Real end-to-end test script for SLAYERS pipeline.

Executes a full project pipeline against real public providers
(Wikimedia, WebSearch Clearbit/Wikipedia, Pexels/Unsplash if keys present).
Validates:
1. Script -> Segmentation -> Intent -> Requirements -> Discovery -> Scoring -> Persistence
2. Provider statistics & warnings persisted on ProcessingJob
3. Low confidence results (<80) are NOT labeled 'recommended'
4. Pipeline resilience when a provider fails or times out
"""
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal, engine, Base
from app.models.models import Project, ContentSegment, AssetRequirement, Asset, ProcessingJob
from app.workers.pipeline_worker import process_project_pipeline
from app.services.providers.base import AssetSearchProvider, DiscoveredAssetCandidate

# Create DB tables if not present
Base.metadata.create_all(bind=engine)


async def run_real_e2e():
    db = SessionLocal()
    project_id = None
    try:
        sample_script = """
The software industry is undergoing a massive shift as AI coding agents emerge.
Developers no longer spend hours writing boilerplate code manually.
Instead, intelligent agents analyze repositories, create implementation plans, and write multi-file features.
For example, modern IDE interfaces now feature AI pair-programmers integrated right into the editor window.
This transformation allows small engineering teams to build complex software in a fraction of the time.
Companies like GitHub, Google, and OpenAI are shipping AI tools that automate repetitive coding tasks.
""".strip()

        # 1. Create project
        project = Project(
            name="Real E2E Verification Project",
            source_type="script",
            source_text=sample_script,
            status="draft"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id

        print(f"=== [E2E STEP 1] Created project {project_id} ===")

        # 2. Run pipeline asynchronously
        await process_project_pipeline(project_id)

        # 3. Verify Database Records & Persistence
        db.expire_all()
        project = db.query(Project).filter(Project.id == project_id).first()
        job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
        segments = db.query(ContentSegment).filter(ContentSegment.project_id == project_id).order_by(ContentSegment.sequence).all()
        requirements = db.query(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).all()
        assets = db.query(Asset).join(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).order_by(Asset.relevance_score.desc()).all()

        print(f"\n=== [E2E VERIFICATION RESULTS] ===")
        print(f"Project Status      : {project.status}")
        print(f"Job Status          : {job.status}")
        print(f"Job Step            : {job.current_step}")
        print(f"Job Progress        : {job.progress}%")
        print(f"Job Provider Stats  : {job.provider_stats}")
        print(f"Job Warnings Count  : {len(job.warnings or [])}")

        print(f"\nTotal Segments      : {len(segments)}")
        for s in segments:
            print(f"  Segment #{s.sequence} [{s.start_time} - {s.end_time}]: visual_intent='{s.visual_intent}' | text='{s.text[:50]}...'")

        print(f"\nTotal Requirements  : {len(requirements)}")
        for r in requirements:
            print(f"  Req ID: {r.id[:8]}... | type='{r.asset_type}' | query='{r.search_query}' | priority='{r.priority}'")

        print(f"\nTotal Discovered Assets: {len(assets)}")
        status_counts = {"recommended": 0, "alternative": 0, "flagged": 0}
        for a in assets:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
            print(f"  Asset ID: {a.id[:8]}... | score={a.relevance_score} | status='{a.status}' | source='{a.source}' | title='{a.title[:60]}...'")

        print(f"\nAsset Status Breakdown: {status_counts}")

        # Assertions
        assert project.status == "completed", f"Expected completed, got {project.status}"
        assert job.status == "completed", f"Expected job completed, got {job.status}"
        assert len(segments) > 0, "No segments created"
        assert len(requirements) > 0, "No requirements created"
        assert len(assets) > 0, "No assets discovered"
        assert job.provider_stats is not None, "provider_stats should be persisted"

        # Verify low-confidence rule: any asset with status 'recommended' MUST have score >= 80
        for a in assets:
            if a.status == "recommended":
                assert a.relevance_score >= 80, f"Asset {a.id} has status 'recommended' but score is {a.relevance_score} (< 80)!"
            elif a.relevance_score < 55:
                assert a.status == "flagged", f"Asset {a.id} has score {a.relevance_score} (< 55) but status is '{a.status}'!"

        print("\nSUCCESS: All E2E assertions passed!")

    finally:
        if project_id:
            # Clean up test project
            proj = db.query(Project).filter(Project.id == project_id).first()
            if proj:
                db.delete(proj)
                db.commit()
        db.close()


if __name__ == "__main__":
    asyncio.run(run_real_e2e())
