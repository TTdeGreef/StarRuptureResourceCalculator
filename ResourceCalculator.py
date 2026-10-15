import numpy as np
import math
import graphviz
from collections import defaultdict

resource_registry = {}
recipe_registry = {}
building_registry = {}


class Resource:
    def __init__(self, name):
        self.name = name
        self.recipes = {}

        self.register()

    def register(self):
        resource_registry[self.name] = self


class Recipe:
    def __init__(
        self,
        name,
        inputs,
        input_amounts,
        output,
        output_amount,
        crafting_time,
        building,
        root_resource=False,
    ):
        self.name = name
        self.building = building

        self.inputs = inputs
        self.input_amounts = np.array(input_amounts)

        self.output = output
        self.output_amount = output_amount

        self.crafting_time = crafting_time
        self.production_per_min = self.output_amount * 60 / self.crafting_time
        self.input_amounts_per_min = self.input_amounts * 60 / self.crafting_time

        self.root_resource = root_resource
        self.register()

    def register(self):
        recipe_registry[self.name] = self
        resource_registry[self.output].recipes[self.name] = self
        building_registry[self.building].recipes[self.name] = self

    def get_supply(self, amount_per_minute, resource_list={}):
        output = resource_registry[self.output]
        n_crafters = amount_per_minute / self.production_per_min
        resource_list[output.name] = n_crafters + resource_list.get(output.name, 0)
        for i, resource_name in enumerate(self.inputs):
            resource = resource_registry[resource_name]
            recipe_registry[resource.name].get_supply(n_crafters * self.input_amounts_per_min[i], resource_list)
        return resource_list

    def get_recipe_tier(self):
        if self.root_resource:
            return 0

        input_resource_tiers = []
        for resource_name in self.inputs:
            resource = resource_registry[resource_name]
            recipes = list(resource.recipes.values())

            if len(recipes) != 1:
                print("Recipes length error")
                for recipe in recipes:
                    print(recipe.name)
                return 0  # WIP

            first_recipe = recipes[0]
            input_resource_tiers.append(first_recipe.get_recipe_tier())
        return max(input_resource_tiers) + 1 if input_resource_tiers else 0


class Building:
    def __init__(self, name):
        self.name = name

        self.recipes = {}

        self.register()

    def register(self):
        building_registry[self.name] = self


def print_planning(resource_name, amount_per_min, rail_speed=480):
    required_supply = recipe_registry[resource_name].get_supply(amount_per_min)
    for recipe_name, n_crafters in required_supply.items():
        recipe = recipe_registry[recipe_name]
        total_production = recipe.production_per_min * n_crafters
        print(f"{n_crafters:.2f}x {recipe.building}s, producing a total of {total_production:.0f} {recipe.name}s per minute")
        if total_production > rail_speed:
            print("Total production exceeds maximum rial speed, proper pathing might be required!")


def graph_planning(resource_name, amount_per_min, rail_speed=480):
    dot = graphviz.Digraph(format="svg")
    dot.attr("node", shape="box")
    dot.attr(rankdir="TB")  # Top-to-bottom flow

    required_supply = recipe_registry[resource_name].get_supply(amount_per_min)

    # Group recipe nodes by tier
    tiers = defaultdict(list)
    for recipe_name, n_crafters in required_supply.items():
        recipe = recipe_registry[recipe_name]
        tier = recipe.get_recipe_tier()
        tiers[tier].append((recipe_name, n_crafters))

    # Add subgraphs for each tier (higher tier at top)
    sorted_tiers = sorted(tiers.keys(), reverse=True)
    previous_rank_first_node = None

    for tier in sorted_tiers:
        nodes = tiers[tier]
        with dot.subgraph() as s:
            s.attr(rank="same")
            for recipe_name, n_crafters in nodes:
                s.node(recipe_name, f"{recipe_name}\nx{n_crafters:.2f}")

        # Force vertical hierarchy between tiers if no explicit edges exist
        first_node_in_tier = nodes[0][0]
        if previous_rank_first_node:
            dot.edge(previous_rank_first_node, first_node_in_tier, style="invis")
        previous_rank_first_node = first_node_in_tier

    # Render edges and check throughput against rail_speed
    for recipe_name, n_crafters in required_supply.items():
        recipe = recipe_registry[recipe_name]

        # Calculate total output production rate for this recipe
        # (Total items/min produced by these n_crafters)
        total_production = n_crafters * recipe.production_per_min

        for input_name in getattr(recipe, "inputs", []):
            if input_name in required_supply:
                # Highlight in RED if total throughput exceeds the rail capacity
                if total_production > rail_speed:
                    dot.edge(
                        input_name,
                        recipe_name,
                        color="red",
                        penwidth="2.5",
                        label=f"{total_production:.0f}/min",
                        fontcolor="red",
                    )
                else:
                    dot.edge(input_name, recipe_name, color="gray40", penwidth="1.2", label=f"{total_production:.0f}/min")

    dot.render("Planning Graph", view=False)


def print_all_resource_tiers(descending=False):
    item_tiers = []
    unknown_items = []
    for resource_name, resource in resource_registry.items():
        recipes = list(resource.recipes.values())
        try:
            item_tiers.append((recipes[0].get_recipe_tier(), resource_name))
        except (IndexError, KeyError):
            # No recipe for this item or one of its ingredients
            unknown_items.append(resource_name)

    item_tiers.sort(key=lambda item: (-item[0] if descending else item[0], item[1]))
    for tier, resource_name in item_tiers:
        print(f"Tier {tier}: {resource_name}")
    for resource_name in sorted(unknown_items):
        print(f"Tier ?: {resource_name} (missing recipe in chain)")


def init_data():
    # Buildings

    Building("Ore Excavator")
    Building("Helium-3 Extractor")
    Building("Sulfur Extractor")
    Building("Laser Drill")
    Building("Oil Extractor")

    Building("Smelter")
    Building("Fabricator")
    Building("Furnace")
    Building("Pressurizer")
    Building("Mega Press")
    Building("Assembler")
    Building("Compounder")
    Building("Pyro Forge")

    # Base Resources and Recipes

    Resource("Wolfram Ore")
    Recipe("Wolfram Ore", [], [], "Wolfram Ore", 2, 2, "Ore Excavator", True)
    Resource("Titanium Ore")
    Recipe("Titanium Ore", [], [], "Titanium Ore", 2, 2, "Ore Excavator", True)
    Resource("Calcium Ore")
    Recipe("Calcium Ore", [], [], "Calcium Ore", 2, 2, "Ore Excavator", True)
    Resource("Helium-3")
    Recipe("Helium-3", [], [], "Helium-3", 2, 2, "Helium-3 Extractor", True)
    Resource("Sulphur Ore")
    Recipe("Sulphur Ore", [], [], "Sulphur Ore", 2, 2, "Sulfur Extractor", True)
    Resource("Goethite Ore")
    Recipe("Goethite Ore", [], [], "Goethite Ore", 1, 4, "Laser Drill", True)
    Resource("Crude Oil")
    Recipe("Crude Oil", [], [], "Crude Oil", 1, 6, "Oil Extractor", True)

    # Crafted Resources and Recipes

    # Smelter

    Resource("Wolfram Bar")
    Recipe("Wolfram Bar", ["Wolfram Ore"], [2], "Wolfram Bar", 2, 2, "Smelter")

    Resource("Titanium Bar")
    Recipe("Titanium Bar", ["Titanium Ore"], [2], "Titanium Bar", 2, 2, "Smelter")

    Resource("Calcium Block")
    Recipe("Calcium Block", ["Calcium Ore"], [2], "Calcium Block", 2, 2, "Smelter")

    # Fabricator
    Resource("Applicator")
    Recipe("Applicator", ["Tube", "Glass"], [8, 2], "Applicator", 1, 4, "Fabricator")

    Resource("Basic Building Material")
    Recipe("Basic Building Material", ["Wolfram Ore", "Titanium Ore"], [1, 1], "Basic Building Material", 10, 2, "Fabricator")

    Resource("Calcite Sheets")
    Recipe("Calcite Sheets", ["Calcium Block"], [1], "Calcite Sheets", 2, 2, "Fabricator")

    Resource("Pistol Ammo")
    Recipe("Pistol Ammo", ["Basic Building Material"], [14], "Pistol Ammo", 25, 4, "Fabricator")

    Resource("Rotor")
    Recipe("Rotor", ["Titanium Rod", "Wolfram Wire"], [2, 2], "Rotor", 1, 6, "Fabricator")

    Resource("Stabilizer")
    Recipe("Stabilizer", ["Rotor", "Titanium Rod"], [1, 2], "Stabilizer", 1, 3, "Fabricator")

    Resource("Stator")
    Recipe("Stator", ["Titanium Housing", "Wolfram Wire"], [2, 1], "Stator", 1, 3, "Fabricator")

    Resource("Titanium Beam")
    Recipe("Titanium Beam", ["Titanium Bar"], [2], "Titanium Beam", 3, 3, "Fabricator")

    Resource("Titanium Rod")
    Recipe("Titanium Rod", ["Titanium Bar"], [1], "Titanium Rod", 1, 2, "Fabricator")

    Resource("Titanium Sheet")
    Recipe("Titanium Sheet", ["Titanium Bar"], [1], "Titanium Sheet", 2, 2, "Fabricator")

    Resource("Tube")
    Recipe("Tube", ["Titanium Rod", "Titanium Sheet"], [1, 1], "Tube", 2, 2, "Fabricator")

    Resource("Wolfram Plate")
    Recipe("Wolfram Plate", ["Wolfram Bar"], [2], "Wolfram Plate", 2, 2, "Fabricator")

    Resource("Wolfram Wire")
    Recipe("Wolfram Wire", ["Wolfram Bar"], [1], "Wolfram Wire", 2, 4, "Fabricator")

    # Furnace

    Resource("Calcium Powder")
    Recipe("Calcium Powder", ["Calcium Block"], [1], "Calcium Powder", 3, 3, "Furnace")

    Resource("Ceramics")
    Recipe("Ceramics", ["Calcite Sheets", "Wolfram Powder"], [1, 1], "Ceramics", 2, 2, "Furnace")

    Resource("Chemicals")
    Recipe("Chemicals", ["Synthetic Silicon", "Wolfram Powder", "Helium-3"], [1, 3, 1], "Chemicals", 2, 2, "Furnace")

    Resource("Electronics")
    Recipe("Electronics", ["Synthetic Silicon", "Inductor", "Stator"], [2, 1, 1], "Electronics", 1, 5, "Furnace")

    Resource("Glass")
    Recipe("Glass", ["Helium-3", "Calcium Powder"], [1, 2], "Glass", 1, 3, "Furnace")

    Resource("Hardening Agent")
    Recipe(
        "Hardening Agent", ["Sulphuric Acid", "Synthetic Silicon", "Applicator"], [5, 1, 1], "Hardening Agent", 2, 4, "Furnace"
    )

    Resource("Heat Resistant Sheet")
    Recipe(
        "Heat Resistant Sheet", ["Wolfram Plate", "Titanium Sheet", "Glass"], [1, 2, 1], "Heat Resistant Sheet", 1, 4, "Furnace"
    )

    Resource("Inductor")
    Recipe("Inductor", ["Tube", "Wolfram Wire", "Ceramics"], [2, 1, 2], "Inductor", 2, 4, "Furnace")

    Resource("Supermagnet")
    Recipe("Supermagnet", ["Sulphuric Acid", "Wolfram Plate", "Chemicals"], [4, 4, 1], "Supermagnet", 1, 3, "Furnace")

    Resource("Synthetic Silicon")
    Recipe("Synthetic Silicon", ["Calcium Powder", "Helium-3", "Ceramics"], [2, 1, 2], "Synthetic Silicon", 2, 2, "Furnace")

    Resource("Titanium Housing")
    Recipe("Titanium Housing", ["Titanium Beam", "Titanium Sheet"], [1, 2], "Titanium Housing", 1, 2, "Furnace")

    Resource("Wolfram Powder")
    Recipe("Wolfram Powder", ["Wolfram Bar"], [1], "Wolfram Powder", 3, 2, "Furnace")

    # Pressurizer

    Resource("Pressurized Helium")
    Recipe("Pressurized Helium", ["Helium-3", "Sulphur Ore"], [1, 1], "Pressurized Helium", 1, 2, "Pressurizer")

    Resource("Sulphuric Acid")
    Recipe("Sulphuric Acid", ["Sulphur Ore", "Chemicals"], [8, 4], "Sulphuric Acid", 4, 2, "Pressurizer")

    # Mega Press

    Resource("Battery")
    Recipe("Battery", ["Inductor", "Electronics", "Sulphuric Acid"], [2, 1, 1], "Battery", 1, 4, "Mega Press")

    Resource("Electromagnetic Coil")
    Recipe(
        "Electromagnetic Coil",
        ["Inductor", "Pressurized Helium", "Wolfram Plate", "Supermagnet"],
        [1, 1, 6, 1],
        "Electromagnetic Coil",
        1,
        4,
        "Mega Press",
    )

    Resource("Goethite Lattice")
    Recipe(
        "Goethite Lattice",
        ["Goethite Ingot", "Titanoferrite Ingot", "Wolfram Steel Ingot"],
        [2, 2, 2],
        "Goethite Lattice",
        2,
        3,
        "Mega Press",
    )

    Resource("Heat Shield")
    Recipe(
        "Heat Shield",
        ["Epoxy", "Aerogel", "Uberfilament", "Reinforced Frame"],
        [3, 3, 3, 2],
        "Heat Shield",
        2,
        10,
        "Mega Press",
    )

    Resource("Heavy Ammo")
    Recipe("Heavy Ammo", ["Basic Building Material", "Titanium Rod"], [24, 6], "Heavy Ammo", 15, 6, "Mega Press")

    Resource("Impeller")
    Recipe(
        "Impeller",
        ["Titanium Rod", "Heat Resistant Sheet", "Wolfram Plate", "Stabilizer"],
        [2, 2, 1, 1],
        "Impeller",
        1,
        4,
        "Mega Press",
    )

    Resource("Intermediate Building Material")
    Recipe(
        "Intermediate Building Material",
        ["Basic Building Material", "Inductor", "Glass", "Titanium Housing"],
        [40, 2, 2, 2],
        "Intermediate Building Material",
        25,
        6,
        "Mega Press",
    )

    Resource("Ion Stabilizer")
    Recipe(
        "Ion Stabilizer",
        ["Epoxy", "Liquid Helium", "Onboard Instruments", "Explosive Charge"],
        [1, 3, 1, 1],
        "Ion Stabilizer",
        1,
        10,
        "Mega Press",
    )

    Resource("Nozzle")
    Recipe("Nozzle", ["Heat Resistant Sheet", "Helium-3", "Stabilizer"], [2, 6, 1], "Nozzle", 1, 5, "Mega Press")

    Resource("Pump")
    Recipe("Pump", ["Valve", "Turbine", "Impeller", "Sulphuric Acid"], [1, 1, 1, 3], "Pump", 1, 10, "Mega Press")

    Resource("Reinforced Frame")
    Recipe(
        "Reinforced Frame", ["Tube", "Titanoferrite Ingot", "Titanium Beam"], [4, 4, 2], "Reinforced Frame", 1, 5, "Mega Press"
    )

    Resource("Reinforced Housing")
    Recipe(
        "Reinforced Housing",
        ["Titanium Housing", "Wolfram Steel Ingot", "Wolfram Plate"],
        [1, 4, 3],
        "Reinforced Housing",
        1,
        4,
        "Mega Press",
    )

    Resource("Shotgun Ammo")
    Recipe("Shotgun Ammo", ["Basic Building Material", "Calcium Powder"], [20, 6], "Shotgun Ammo", 15, 6, "Mega Press")

    Resource("Standard Ammo")
    Recipe("Standard Ammo", ["Basic Building Material", "Wolfram Powder"], [18, 4], "Standard Ammo", 20, 6, "Mega Press")

    Resource("Turbine")
    Recipe("Turbine", ["Impeller", "Stator", "Rotor", "Sulphuric Acid"], [1, 1, 2, 2], "Turbine", 1, 6, "Mega Press")

    Resource("Valve")
    Recipe("Valve", ["Titanium Housing", "Titanium Beam", "Titanium Rod", "Nozzle"], [1, 3, 2, 1], "Valve", 1, 10, "Mega Press")

    # Assembler

    Resource("Accumulator")
    Recipe("Accumulator", ["Electronics", "Stator", "Battery"], [2, 1, 1], "Accumulator", 1, 5, "Assembler")

    Resource("Condenser")
    Recipe("Condenser", ["Resonator", "Pump", "Nanofibre"], [1, 3, 8], "Condenser", 1, 15, "Assembler")

    Resource("Electromagnet")
    Recipe(
        "Electromagnet",
        ["Electromagnetic Coil", "Synthetic Resin", "Accumulator"],
        [3, 3, 1],
        "Electromagnet",
        1,
        5,
        "Assembler",
    )

    Resource("Explosive Charge")
    Recipe("Explosive Charge", ["Reinforced Housing", "Epoxy"], [2, 1], "Explosive Charge", 1, 6, "Assembler")

    Resource("Generator")
    Recipe("Generator", ["Turbine", "Battery", "Nozzle"], [1, 1, 1], "Generator", 1, 10, "Assembler")

    Resource("Laser Emitter")
    Recipe("Laser Emitter", ["Lens", "Resonator", "Electromagnetic Coil"], [1, 1, 6], "Laser Emitter", 1, 6, "Assembler")

    Resource("Onboard Instruments")
    Recipe(
        "Onboard Instruments",
        ["Electronics", "Stabilizer", "Reinforced Housing"],
        [1, 2, 1],
        "Onboard Instruments",
        1,
        5,
        "Assembler",
    )

    Resource("Plastic Dust")
    Recipe("Plastic Dust", ["Organic Compound", "Basic Fuel", "Plastic"], [2, 1, 2], "Plastic Dust", 2, 10, "Assembler")

    Resource("Pressure Tank")
    Recipe("Pressure Tank", ["Heat Resistant Sheet", "Valve", "Pump"], [5, 2, 2], "Pressure Tank", 1, 10, "Assembler")

    Resource("Pseudorubber Insulator")
    Recipe(
        "Pseudorubber Insulator",
        ["Plastic", "Epoxy", "Goethite Lattice"],
        [5, 2, 3],
        "Pseudorubber Insulator",
        2,
        12,
        "Assembler",
    )

    Resource("Resonator")
    Recipe("Resonator", ["Accumulator", "Generator", "Liquid Helium"], [1, 2, 2], "Resonator", 1, 10, "Assembler")

    Resource("Scanner")
    Recipe("Scanner", ["Lens", "Generator", "Stabilizer"], [3, 3, 12], "Scanner", 1, 10, "Assembler")

    Resource("Uberfilament")
    Recipe("Uberfilament", ["Calcium Powder", "Goethite Lattice", "Epoxy"], [6, 2, 1], "Uberfilament", 1, 4, "Assembler")

    # Compounder

    Resource("Aerogel")
    Recipe("Aerogel", ["Goethite Powder", "Calcium Powder", "Liquid Helium"], [4, 6, 2], "Aerogel", 2, 6, "Compounder")

    Resource("Basic Fuel")
    Recipe("Basic Fuel", ["Wolfram Powder", "Goethite Powder", "Liquid Helium"], [4, 2, 4], "Basic Fuel", 1, 6, "Compounder")

    Resource("Epoxy")
    Recipe("Epoxy", ["Liquid Helium", "Goethite Powder", "Synthetic Resin"], [1, 3, 1], "Epoxy", 2, 3, "Compounder")

    Resource("Goethite Powder")
    Recipe(
        "Goethite Powder",
        ["Goethite Ingot", "Pressurized Helium", "Calcium Powder"],
        [1, 1, 1],
        "Goethite Powder",
        4,
        2,
        "Compounder",
    )

    Resource("Ion Injector")
    Recipe("Ion Injector", ["Applicator", "Electromagnet", "Pressure Tank"], [8, 2, 1], "Ion Injector", 1, 12, "Compounder")

    Resource("Lens")
    Recipe("Lens", ["Glass", "Hardening Agent", "Synthetic Resin"], [10, 6, 4], "Lens", 1, 10, "Compounder")

    Resource("Liquid Helium")
    Recipe("Liquid Helium", ["Pressurized Helium", "Hardening Agent"], [1, 1], "Liquid Helium", 1, 3, "Compounder")

    Resource("Nanofibre")
    Recipe("Nanofibre", ["Tube", "Liquid Helium", "Wolfram Wire"], [20, 5, 8], "Nanofibre", 2, 6, "Compounder")

    Resource("Organic Compound")
    Recipe("Organic Compound", ["Sulphuric Acid", "Refined Oil", "Epoxy"], [1, 2, 1], "Organic Compound", 3, 4, "Compounder")

    Resource("Plastic")
    Recipe("Plastic", ["Refined Oil", "Sulphuric Acid", "Chemicals"], [3, 1, 1], "Plastic", 5, 10, "Compounder")

    Resource("Substance #FHS-135-493")
    Recipe(
        "Substance #FHS-135-493",
        ["Sulphuric Acid", "Goethite Powder", "Liquid Helium"],
        [1, 3, 2],
        "Substance #FHS-135-493",
        1,
        6,
        "Compounder",
    )

    Resource("Superconductor")
    Recipe(
        "Superconductor", ["Synthetic Resin", "Electromagnet", "Supermagnet"], [4, 2, 6], "Superconductor", 1, 5, "Compounder"
    )

    Resource("Synthetic Protein")
    Recipe(
        "Synthetic Protein",
        ["Organic Compound", "Substance #FHS-135-493", "Sulphuric Acid"],
        [2, 1, 2],
        "Synthetic Protein",
        1,
        6,
        "Compounder",
    )

    Resource("Synthetic Resin")
    Recipe(
        "Synthetic Resin",
        ["Hardening Agent", "Sulphuric Acid", "Calcite Sheets"],
        [1, 3, 6],
        "Synthetic Resin",
        1,
        3,
        "Compounder",
    )

    # Pyro Forge

    Resource("Goethite Ingot")
    Recipe("Goethite Ingot", ["Goethite Ore"], [1], "Goethite Ingot", 10, 4, "Pyro Forge")

    Resource("Titanoferrite Ingot")
    Recipe("Titanoferrite Ingot", ["Titanium Ore", "Goethite Ore"], [10, 1], "Titanoferrite Ingot", 10, 4, "Pyro Forge")

    Resource("Wolfram Steel Ingot")
    Recipe("Wolfram Steel Ingot", ["Wolfram Ore", "Goethite Ore"], [10, 1], "Wolfram Steel Ingot", 10, 4, "Pyro Forge")


init_data()
graph_planning("Heat Shield", 6)
print_all_resource_tiers()
