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


def init_data():
    # Buildings

    Building("Ore Excavator")
    Building("Helium-3 Extractor")
    Building("Sulfur Extractor")

    Building("Smelter")
    Building("Fabricator")
    Building("Furnace")
    Building("Pressurizer")

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
    Recipe("Basic Buidling Material", ["Wolfram Ore", "Titanium Ore"], [1, 1], "Basic Building Material", 10, 2, "Fabricator")

    Resource("Calcite Sheets")
    Recipe("Calcite Sheets", ["Calcium Block"], [1], "Calcite Sheets", 2, 2, "Fabricator")

    Resource("Pistol Ammo")
    Recipe("Pistol Ammo", ["Basic Building Material"], [14], "Pistol Ammo", 25, 4, "Fabricator")

    Resource("Rotor")
    Recipe("Rotor", ["Titanium Rod", "Wolfram Wire"], [2, 2], "Rotor", 1, 6, "Fabricator")

    Resource("Stabelizer")
    Recipe("Stabelizer", ["Rotor", "Titanium Rod"], [1, 2], "Stabelizer", 1, 3, "Fabricator")

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


init_data()
graph_planning("Synthetic Silicon", 480)
