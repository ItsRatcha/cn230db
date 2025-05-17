# CN230 Project Template

    python db.py


1. fork this repository
2. run codespaces
3. when done execute the following git command

```
    git add .
    git commit -m "finished"
    git push origin main
```
### How to run
1. run [download_move.py](download_move.py)
3. run [download_pokemon.py](download_pokemon.py)
4. run [download_type.py](download_type.py)
5. run [generate_report.ipynb](generate_report.ipynb)

---
# Pokémon Data Analysis Project

## Objective

To analyze Pokémon data from the [PokéAPI](https://pokeapi.co/) using modern data science techniques. The goal was to identify trends, outliers, and optimal characteristics such as strongest Pokémon, most effective types, and most powerful moves.

## Data Source

- **API**: [PokéAPI](https://pokeapi.co/)
- **Scope**: 1,025 Pokémon from Generation I through Generation IX (up to _Scarlet & Violet_)

## Problem

While Pokémon stats and data are extensive, the official games don't always make it easy to compare or analyze trends. This project seeks to answer:

- Who are the strongest non-legendary Pokémon?
- What are the most effective Pokémon types?
- How do different generations compare?
- What are the best moves per type—and can we even define "best"?
- 
---
## Methodology & Main Analysis

### Base Stat Breakdown
- Explained the meaning of each stat: HP, Attack, Defense, Sp. Atk, Sp. Def, Speed.
- Calculated **Base Stat Total (BST)** as a simple sum of all six stats.

### Strongest Pokémon
- Ranked all fully-evolved Pokémon by BST.
- Removed legendaries to find **strongest "normal" Pokémon**.

### Attack + Speed Filter
- Found Pokémon with **high Attack** and **above-average Speed**, ideal for offensive play.

### Weakness Analysis
- Counted how many Pokémon are weak to each type.
- Top threats by weakness count:
    1. **Ice** 
    2. **Ground** 
    3. **Fairy**  
        _(others followed)_

### Type-Based Averages
- **Strongest Type (BST)**: Type with highest average Base Stat Total.
- **Weakest Type (BST)**: Type with lowest average BST.
- **Fastest Type**: Highest average Speed.
- **Bulkiest Type**: Highest average `[HP + (Defense + Sp. Def) / 2]`.

### Generation Comparison
- Calculated average BST by generation. 
- Found strongest and weakest generations statistically.

### Move Power by Type
- Found the strongest move per type based on `power` field.
- Issues found:
    - Some high-power moves (e.g., Explosion) are impractical.
    - Power alone doesn't reflect turn restrictions, availability, or recoil.
- **Conclusion**: move strength needs _contextual analysis_, not raw power alone.

---
## Results Summary
- **Strongest Pokémon (non-legendary)**: Solgaleo
- **Stronest Attacking Pokémon**: Kartana and xurkitree
- **Most Weakness-Covering Type**: Ice
- **Best Type Overall**: Dragon
- **Strongest Generation**: 7
- **Fastest Type**: Electric
- **Bulkiest Type**: Steel

---

## Conclusion

The PokéAPI provides an incredibly rich dataset for analysis. This project revealed the limitations of surface-level stat comparisons and emphasized the need for contextual filtering. Not all high-power moves are practical, and bulk/speed vary greatly by type and generation. Game balance has evolved significantly across generations, and data science can help highlight what works—and what just looks good on paper.

---

## References

- [PokéAPI Documentation](https://pokeapi.co/docs/v2)
- [Bulbapedia](https://bulbapedia.bulbagarden.net/) (for secondary validation of data)
- [Serebii](https://www.serebii.net/) (for move descriptions and generation differences)
