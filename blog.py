import sqlite3
from builtins import staticmethod
import argparse
from collections import Counter



TABLES = ['meal', 'ingredient', 'measure']

RECIPE_DATA = {"meals": ("breakfast", "brunch", "lunch", "supper"),
               "ingredients": ("milk", "cacao", "strawberry", "blueberry", "blackberry", "sugar"),
               "measures": ("ml", "g", "l", "cup", "tbsp", "tsp", "dsp", "")}

class Recipes:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.initialize_DB()
        self.conn.commit()
        print('Pass the empty recipe name to exit.')

    def initialize_DB(self):
        # create first tables from RECIPE_DATA dictionary
        for name in TABLES:
            self.cursor.execute(self.create_table_query(name))
            for item in RECIPE_DATA[name + "s"]:
                print(self.insert_item_query(name, item))
                self.cursor.execute(self.insert_item_query(name, item))
        # TODO: Pack up these tables into functions,
        # TODO: investigate more generic create function table
        self.cursor.execute(self.create_recipes_table_query())
        self.cursor.execute(self.create_serve_table_query())
        self.cursor.execute(self.create_quantity_table_query())

    @staticmethod
    def create_table_query(name) -> str:
        return f"""
        CREATE TABLE IF NOT EXISTS {name}s  ( 
        {name}_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        {name}_name VARCHAR(30) {"NOT NULL" if name != "measure" else ""} UNIQUE);
        """

    @staticmethod
    def create_recipes_table_query() -> str:
        return f"""
            CREATE TABLE IF NOT EXISTS recipes  ( 
            recipe_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            recipe_name TEXT NOT NULL,
            recipe_description TEXT)
            """

    @staticmethod
    def create_serve_table_query() -> str:
        return f"""
            CREATE TABLE IF NOT EXISTS serve(
            serve_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            recipe_id INTEGER NOT NULL,
            meal_id INTEGER NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
            FOREIGN KEY (meal_id) REFERENCES meals(meal_id));
            """

    @staticmethod
    def create_quantity_table_query() -> str:
        return f"""
            CREATE TABLE IF NOT EXISTS quantity(
            quantity_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            quantity INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            measure_id INTEGER NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id),
            FOREIGN KEY (measure_id) REFERENCES measures(measure_id));
            """

    @staticmethod
    def insert_item_query(_name, _item) -> str:
        return f"""
        INSERT INTO {_name}s ({_name}_name) VALUES ("{_item}")
        """

    @staticmethod
    def insert_recipe_query(_name, _recipe) -> str:
        return f"""
        INSERT INTO recipes (recipe_name, recipe_description) 
        VALUES ("{_name}", "{_recipe}");
        """

    @staticmethod
    def insert_serve_query(_meal_id, _recipe_id) -> str:
        return f"""\
        INSERT INTO serve (meal_id, recipe_id) VALUES ({_meal_id},{_recipe_id});\
        """

    @staticmethod
    def insert_quantity_query(_recipe_id, _ingredient_id, measure_id, _quantity) -> str:
        return f"""
        INSERT INTO quantity (recipe_id, ingredient_id, measure_id, quantity) 
        VALUES ({_recipe_id},{_ingredient_id}, {measure_id}, {_quantity});
        """

    def is_in_table_query(self, _table, _item_name):
        # return True if item is in table, else return False
        return \
            len(self.cursor.execute(f"""
            SELECT * FROM {_table}s WHERE {_table}_name = '{_item_name}'"
        """).fetchall()) > 0

    def is_unique_query(self, _table, _string):
        """
         Purpose of this function is to find if the substring (or string) of an item
         we're looking for is enough to indentify a single unique item in the table.
         If the string we're looking for is an empty string then look for items
         equal to it (as '' would be found in all items), else use "LIKE" keyword
         """
        if _string == '':
            arr = self.cursor.execute(f"SELECT * FROM {_table}s "
                                      f"WHERE {_table}_name = '{_string}'").fetchall()
        else:
            arr = self.cursor.execute(f"SELECT * FROM {_table}s "
                                      f"WHERE {_table}_name LIKE '%{_string}%'").fetchall()
        # return tuple of two items:
        # 1/ true if only one item is found, else return false
        # 2/ if only one item found, returns its id, else return -1
        return len(arr) == 1, arr[0][0] if len(arr) == 1 else -1

    def add_recipes(self):
        # look to add recipes
        _ongoing = True
        while _ongoing:
            _ongoing = self.get_recipe()

    def get_recipe(self) -> str:
        # TODO: Simplify this function or split it
        name = input('Recipe name:')
        if len(name) > 0:
            recipe = input('Recipe description: ')
            recipe_id = self.cursor.execute(self.insert_recipe_query(name, recipe)).lastrowid
            print('1) breakfast  2) brunch  3) lunch  4) supper')
            serving = input('When the dish can be served:').split()
            for s in serving:
                try:
                    self.cursor.execute(self.insert_serve_query(int(s), int(recipe_id)))
                except Exception as e:
                    print(e)
            ingredient = 'init'
            while len(ingredient) > 0:
                ingredient = input("Input quantity of ingredient <press enter to stop>:").split()
                if len(ingredient) == 0:
                    break
                ingredient_amount = ingredient[0]
                ingredient_name = ingredient[-1]
                if len(ingredient) == 3:
                    ingredient_measure = ingredient[1]
                else:
                    ingredient_measure = ""
                measure_unique, measure_id = self.is_unique_query("measure", ingredient_measure)
                ingredient_unique, ingredient_id = self.is_unique_query("ingredient", ingredient_name)
                if measure_unique:
                    if ingredient_unique:
                        self.cursor.execute(self.insert_quantity_query(
                            recipe_id, ingredient_id, measure_id, ingredient_amount))
                    else:
                        print("The ingredient is not conclusive!")
                else:
                    print("The measure is not conclusive!")
            self.conn.commit()
            return True
        else:
            self.exit_recipes()
            return False

    def exit_recipes(self):
        self.conn.commit()
        self.conn.close()

    def __del__(self):
        # backup for unexpected class del without using exit_recipes method
        try:
            self.conn.commit()
            self.conn.close()
        except:
            # already closed
            pass

class RetrieveRecipes:
    def __init__(self, meals, ingredients):
        self.meals = meals.split(',')
        self.ingredients = ingredients.split(',')
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()

    def get_meals_ids(self):
        _meals_str = ', '.join(f'"{meal}"' for meal in self.meals)
        _meals = self.cursor.execute(f"SELECT * FROM meals "
                                     f"WHERE meal_name IN "
                                     f"({_meals_str})")\
            .fetchall()
        return [item[0] for item in _meals]


    def get_ingredient_ids(self):
        _ingredients_str = ', '.join(f'"{ingredient}"' for ingredient in self.ingredients)
        _ingredients = self.cursor.execute(f"SELECT * FROM ingredients "
                                     f"WHERE ingredient_name IN "
                                     f"({_ingredients_str})")\
            .fetchall()
        return [item[0] for item in _ingredients]

    def retrieve_recipes(self):
        # prepare strings for SQL queries
        _ingredients_str = ', '.join(f'"{ingredient}"' for ingredient in self.ingredients)
        _meals_str = ', '.join(f'"{meal}"' for meal in self.meals)
        # get recipe_ids corresponding to wanted ingredients
        _recipes = self.cursor.execute\
        (f"""
        SELECT recipe_id FROM quantity WHERE ingredient_id IN
        (SELECT ingredient_id FROM ingredients WHERE ingredient_name IN ({_ingredients_str}))
        """).fetchall()
        # get counts of wanted recipe occurences by recipe id
        ingredient_count = Counter(_recipes)
        # get recipe_ids corresponding to wanted meal types
        _recipes_meals = self.cursor.execute\
            (f"""
        SELECT recipe_id FROM serve WHERE meal_id IN 
        (SELECT meal_id FROM meals WHERE meal_name IN ({_meals_str}))
        """).fetchall()
        # reformat list
        _recipes_meals = [x[0] for x in _recipes_meals]
        viable_recipe_ids = []
        # only select recipes that are for wanted meal types and contain n_ingredientss (all) ingredients
        n_ingredinets = len(self.ingredients)
        for item in ingredient_count:
            if (item[0] in _recipes_meals) and ingredient_count[item] == n_ingredinets:
                viable_recipe_ids.append(item[0])

        for id in viable_recipe_ids:
            suggested_recipe = self.cursor.execute \
            (f"""
            SELECT recipe_name FROM recipes 
            WHERE recipe_id = {id}
            """).fetchall()
            print(suggested_recipe)
        if len(viable_recipe_ids) == 0:
            print("no such recipes")

        self.conn.close()


parser = argparse.ArgumentParser()
parser.add_argument ('File')
parser.add_argument('--ingredients', type=str, required=False)
parser.add_argument('--meals', type=str, required=False)
args = parser.parse_args()
DB_NAME = args.File

if args.meals is not None:
    get_recipes = RetrieveRecipes(args.meals, args.ingredients)
    get_recipes.retrieve_recipes()
else:
    recipes = Recipes()
    recipes.add_recipes()
