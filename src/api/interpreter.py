import os
import anthropic
import json


client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def build_prompt(request: dict, patterns: list[dict]) -> str:
    pattern_summary = json.dumps(
        [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "pros": p["pros"],
                "cons": p["cons"],
                "geometry_params": p["geometry_params"],
                "fusion_360_notes": p["fusion_360_notes"],
                "cosmetic_sensitivity": p["cosmetic_sensitivity"],
            }
            for p in patterns
        ],
        indent=2,
    )

    function_goal = request.get("function_goal", "semi_permanent")
    goal_descriptions = {
        "semi_permanent": "Semi-permanent assembly: parts should stay together under normal use but allow intentional disassembly with moderate force or a tool. Typical for cosmetic product casings that may need servicing.",
        "single": "Single assembly: parts are assembled once and never intended to be disassembled. Maximum retention force is the priority.",
        "easy_release": "Easy release: parts should snap together firmly but release with light finger pressure. User-friendly opening is the priority.",
        "frequent": "Frequent open/close: parts will be assembled and disassembled many times. Cycle life and low stress per cycle are the priority.",
    }

    goal_description = goal_descriptions.get(function_goal, goal_descriptions["semi_permanent"])

    return f"""You are a design engineer specializing in cosmetic product packaging and plastic joining methods.

A designer is working on the following:
- Product type: {request['product_type']}
- Production method: {request['production_method']}
- Production volume: {request['volume']} units
- Budget tier: {request['budget_tier']}
- Material: {request['material']}
- Assembly function goal: {goal_description}

The following joining patterns have been pre-filtered as compatible with these constraints:

{pattern_summary}

Your task:
1. Rank these patterns from most to least recommended for this specific use case, giving significant weight to the assembly function goal.
2. For each pattern explain in 2-3 sentences why it is or is not ideal for this exact combination of constraints and function goal.
3. For the top recommended pattern only, provide specific Fusion 360 implementation steps tailored to the material, production method, and function goal specified.
4. Flag any constraint combinations that introduce risk even though the pattern technically qualifies.
5. If the function goal strongly suggests a different mechanism not in the filtered list, name it and explain why it was not recommended.

Respond in this exact JSON format:
{{
  "ranked_recommendations": [
    {{
      "rank": 1,
      "id": "pattern_id",
      "name": "Pattern Name",
      "rationale": "Why this pattern suits these exact constraints and function goal.",
      "risks": "Any risks specific to this constraint combination or null if none.",
      "fusion_360_steps": "Detailed steps for top pattern only, null for others."
    }}
  ]
}}

Return only valid JSON. No preamble, no markdown, no explanation outside the JSON.
"""


def interpret(request: dict, patterns: list[dict]) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return mock_interpretation(patterns)

    prompt = build_prompt(request, patterns)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    return json.loads(raw)


def mock_interpretation(patterns: list[dict]) -> dict:
    return {
        "ranked_recommendations": [
            {
                "rank": i + 1,
                "id": p["id"],
                "name": p["name"],
                "rationale": "Mock rationale. Set ANTHROPIC_API_KEY to enable real interpretation.",
                "risks": None,
                "fusion_360_steps": "Mock steps. Set ANTHROPIC_API_KEY to enable real interpretation." if i == 0 else None,
            }
            for i, p in enumerate(patterns)
        ]
    }