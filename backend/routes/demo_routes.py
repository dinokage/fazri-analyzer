"""
Demo API Routes
Provides REST endpoints for interactive alert demonstrations.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.alerts import DemoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


# =============================================================================
# SCENARIO DISCOVERY
# =============================================================================

@router.get("/scenarios")
async def list_scenarios(
    active_only: bool = Query(True, description="Only show active scenarios"),
    db: Session = Depends(get_db),
):
    """
    List all available demo scenarios.

    Returns scenarios with basic info for selection UI.
    """
    service = DemoService(db)
    scenarios = service.get_scenarios(active_only=active_only)

    return {
        "total": len(scenarios),
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "severity": s.severity.value,
                "duration_seconds": s.duration_seconds,
                "default_speed": s.default_speed,
                "auto_advance": s.auto_advance,
            }
            for s in scenarios
        ],
    }


@router.get("/scenarios/{scenario_id}")
async def get_scenario_details(
    scenario_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific scenario.

    Includes full timeline with narration for presentation mode.
    """
    service = DemoService(db)
    details = service.get_scenario_details(scenario_id)

    if not details:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return details


# =============================================================================
# DEMO STATE
# =============================================================================

@router.get("/state")
async def get_demo_state(
    db: Session = Depends(get_db),
):
    """
    Get the current state of the running demo.

    Returns null values if no demo is running.
    """
    service = DemoService(db)
    return service.get_state()


# =============================================================================
# DEMO CONTROLS
# =============================================================================

@router.post("/start/{scenario_id}")
async def start_demo(
    scenario_id: str,
    speed: float = Query(1.0, ge=0.1, le=100, description="Playback speed multiplier"),
    auto_advance: bool = Query(True, description="Auto-advance through timeline"),
    db: Session = Depends(get_db),
):
    """
    Start a demo scenario.

    Args:
        scenario_id: ID of the scenario to run
        speed: Playback speed (1.0 = real time, 10.0 = 10x faster)
        auto_advance: Whether to automatically advance through steps
    """
    service = DemoService(db)

    try:
        state = service.start_scenario(
            scenario_id=scenario_id,
            speed=speed,
            auto_advance=auto_advance,
        )
        return {
            "message": f"Demo '{scenario_id}' started",
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_demo(
    db: Session = Depends(get_db),
):
    """
    Stop the current demo.

    Cleans up the demo alert and resets state.
    """
    service = DemoService(db)
    state = service.stop_demo()

    return {
        "message": "Demo stopped",
        "final_state": state,
    }


@router.post("/pause")
async def pause_demo(
    db: Session = Depends(get_db),
):
    """
    Pause the current demo.

    Stops auto-advance but preserves state.
    """
    service = DemoService(db)

    try:
        state = service.pause_demo()
        return {
            "message": "Demo paused",
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resume")
async def resume_demo(
    db: Session = Depends(get_db),
):
    """
    Resume a paused demo.

    Restarts auto-advance if it was enabled.
    """
    service = DemoService(db)

    try:
        state = service.resume_demo()
        return {
            "message": "Demo resumed",
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/advance")
async def advance_step(
    db: Session = Depends(get_db),
):
    """
    Manually advance to the next step.

    Works regardless of auto-advance setting.
    """
    service = DemoService(db)

    try:
        state = service.advance_step()
        return {
            "message": f"Advanced to step {state['current_step']}",
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/speed")
async def set_speed(
    speed: float = Query(..., ge=0.1, le=100, description="New playback speed"),
    db: Session = Depends(get_db),
):
    """
    Set the demo playback speed.

    Args:
        speed: Playback speed multiplier (0.1 to 100)
    """
    service = DemoService(db)

    try:
        state = service.set_speed(speed)
        return {
            "message": f"Speed set to {speed}x",
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# QUICK START PRESETS
# =============================================================================

@router.post("/quick-start")
async def quick_start_demo(
    preset: str = Query("unauthorized_access", description="Preset scenario to run"),
    db: Session = Depends(get_db),
):
    """
    Quick start a demo with preset configuration.

    Presets:
    - unauthorized_access: 45 second demo at normal speed
    - suspicious_loitering: 50 second demo with escalation
    - coordinated_activity: Critical scenario with multi-staff response
    - after_hours_equipment: Low priority demo at 2x speed
    - escalation_demo: Long demo showing escalation (10x speed recommended)
    """
    presets = {
        "unauthorized_access": {"speed": 3.0, "auto_advance": True},
        "suspicious_loitering": {"speed": 3.0, "auto_advance": True},
        "coordinated_activity": {"speed": 2.0, "auto_advance": True},
        "after_hours_equipment": {"speed": 5.0, "auto_advance": True},
        "escalation_demo": {"speed": 30.0, "auto_advance": True},
    }

    config = presets.get(preset, {"speed": 3.0, "auto_advance": True})

    service = DemoService(db)

    try:
        state = service.start_scenario(
            scenario_id=preset,
            speed=config["speed"],
            auto_advance=config["auto_advance"],
        )
        return {
            "message": f"Quick demo '{preset}' started",
            "preset_config": config,
            "state": state,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
