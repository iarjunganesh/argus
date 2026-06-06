"""
generate_corporate_graph.py
Generates a synthetic corporate ownership graph using NetworkX.
Output: data/synthetic/corporate_graph.jsonl
"""
import json, random
import networkx as nx
from faker import Faker
from pathlib import Path

fake = Faker(); Faker.seed(55); random.seed(55)
OUTPUT = Path(__file__).parent / "corporate_graph.jsonl"

HIGH_RISK_JRSDS = ["PA", "KY", "BVI"]
ALL_JRSDS = ["NL", "DE", "GB", "SE", "CH", "LU"] + HIGH_RISK_JRSDS

def build_graph(n_companies=500, n_individuals=1500):
    G = nx.DiGraph()
    companies    = [fake.company()         for _ in range(n_companies)]
    individuals  = [fake.name()            for _ in range(n_individuals)]

    # Wire ownership edges
    edges = []
    for company in companies:
        n_owners = random.randint(1, 4)
        owners   = random.sample(individuals + companies, min(n_owners, len(individuals)))
        pcts     = _split_ownership(n_owners)
        for owner, pct in zip(owners, pcts):
            edges.append({
                "parent_entity":        company,
                "name":                 owner,
                "entity_type":          "individual" if owner in individuals else "corporate",
                "ownership_percentage": pct,
                "jurisdiction":         random.choice(ALL_JRSDS),
            })
    return edges

def _split_ownership(n: int) -> list[float]:
    """Split 100% into n random shares."""
    if n == 1:
        return [100.0]
    cuts = sorted(random.uniform(0, 100) for _ in range(n - 1))
    shares = [cuts[0]] + [cuts[i] - cuts[i-1] for i in range(1, n-1)] + [100 - cuts[-1]]
    return [round(s, 2) for s in shares]

def main():
    print("Generating synthetic corporate ownership graph...")
    edges = build_graph()
    with open(OUTPUT, "w") as f:
        for e in edges:
            f.write(json.dumps(e) + "\n")
    print(f"Generated {len(edges)} ownership relationships → {OUTPUT}")

if __name__ == "__main__":
    main()
