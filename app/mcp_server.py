from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("ideaforge_mcp_server")

@mcp.tool()
def get_market_trends(industry: str) -> str:
    """Get the latest market size, growth rate, and key trends for a given industry.
    
    Args:
        industry: The industry/niche to analyze (e.g., 'food delivery', 'edtech').
    """
    industry_lower = industry.lower()
    trends = {
        "market_size": "Estimated $15B+ globally by 2028",
        "growth_rate": "CAGR of 8.2%",
        "key_trends": [
            "Increased focus on sustainability and eco-friendly packaging.",
            "Personalization driven by local AI routing algorithms.",
            "Growing demand for direct-to-consumer delivery models."
        ]
    }
    
    if "food" in industry_lower or "restaurant" in industry_lower:
        trends = {
            "market_size": "$220B+ globally",
            "growth_rate": "CAGR of 11.5%",
            "key_trends": [
                "Dark kitchens / Ghost kitchens optimizing overhead costs.",
                "Zero-waste and sustainable food packaging solutions.",
                "Hyper-local sourcing and farm-to-table organic subscriptions."
            ]
        }
    elif "education" in industry_lower or "edtech" in industry_lower or "study" in industry_lower:
        trends = {
            "market_size": "$340B+ globally",
            "growth_rate": "CAGR of 15.3%",
            "key_trends": [
                "Micro-learning modules integrated with social feeds.",
                "Generative AI tutoring and interactive role-playing coaches.",
                "Credentialing of niche skills over traditional degrees."
            ]
        }
        
    return json.dumps(trends, indent=2)

@mcp.tool()
def get_competitor_analysis(product_category: str) -> str:
    """Retrieve primary competitors, their market share, strengths, and weaknesses.
    
    Args:
        product_category: The type of product or service (e.g., 'vegan snacks', 'tutoring app').
    """
    category_lower = product_category.lower()
    competitors = [
        {
            "name": "Market Leader Inc.",
            "share": "45%",
            "strengths": "Deep pockets, strong brand recognition, massive distribution.",
            "weaknesses": "Slow to innovate, poor customer support, high pricing."
        },
        {
            "name": "Niche Startups Co.",
            "share": "15%",
            "strengths": "Agile, modern tech stack, targeted marketing.",
            "weaknesses": "Limited resources, high customer acquisition cost (CAC)."
        }
    ]
    
    if "food" in category_lower or "delivery" in category_lower:
        competitors = [
            {
                "name": "DoorDash / UberEats",
                "share": "70%",
                "strengths": "Gigantic driver network, brand awareness, app integration.",
                "weaknesses": "High commission rates (15-30%) for restaurants, high service fees."
            },
            {
                "name": "Local Delivery Co-ops",
                "share": "5%",
                "strengths": "Supportive local image, lower commissions, high restaurant loyalty.",
                "weaknesses": "Tiny driver pool, restricted service areas, basic mobile apps."
            }
        ]
    elif "edu" in category_lower or "tutor" in category_lower or "learn" in category_lower:
        competitors = [
            {
                "name": "Duolingo / Coursera",
                "share": "55%",
                "strengths": "Gamified engagement, massive library, global recognition.",
                "weaknesses": "Lack of 1-on-1 personalization, low course completion rates."
            },
            {
                "name": "Local Private Tutors",
                "share": "20%",
                "strengths": "High personalization, trust, custom learning pace.",
                "weaknesses": "Extremely expensive, non-scalable, hard scheduling."
            }
        ]
        
    return json.dumps(competitors, indent=2)

@mcp.tool()
def calculate_break_even(fixed_costs: float, selling_price: float, variable_cost: float) -> str:
    """Calculate the break-even volume of units and key unit economics.
    
    Args:
        fixed_costs: Total fixed operating overhead costs (e.g., rent, salaries).
        selling_price: The retail/selling price per unit of service/product.
        variable_cost: The marginal cost to produce/deliver one unit.
    """
    if selling_price <= variable_cost:
        return json.dumps({"error": "Selling price must be strictly greater than variable cost per unit."}, indent=2)
        
    contribution_margin = selling_price - variable_cost
    contribution_margin_ratio = contribution_margin / selling_price
    break_even_units = fixed_costs / contribution_margin
    
    analysis = {
        "contribution_margin_per_unit": contribution_margin,
        "contribution_margin_ratio": f"{contribution_margin_ratio:.2%}",
        "break_even_units": round(break_even_units, 2),
        "break_even_revenue": round(break_even_units * selling_price, 2),
        "guidance": f"To break even, you must sell at least {round(break_even_units)} units. Every sale after that contributes ${contribution_margin:.2f} to net profit."
    }
    return json.dumps(analysis, indent=2)

@mcp.tool()
def generate_brand_assets(business_type: str, keywords_comma_separated: str) -> str:
    """Generate professional brand slogans and taglines based on keywords.
    
    Args:
        business_type: The type of business (e.g., 'Bakery', 'SaaS', 'Tutor').
        keywords_comma_separated: Comma-separated descriptors of the brand's core values.
    """
    keywords = [k.strip() for k in keywords_comma_separated.split(",") if k.strip()]
    if not keywords:
        keywords = ["quality", "innovation"]
        
    kw_str = " & ".join(keywords[:3])
    slogans = [
        f"The Future of {business_type}: Powered by {kw_str}.",
        f"Smart {business_type} — Simple, Reliable, and {keywords[0]}.",
        f"Redefining {business_type} through {kw_str}."
    ]
    return json.dumps({"slogans": slogans}, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
