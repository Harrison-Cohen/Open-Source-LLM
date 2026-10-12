import math
import sympy

OPERATIONS = {
    '1': lambda a, b: a + b,
    '2': lambda a, b: a - b,
    '3': lambda a, b: a * b,
    '4': lambda a, b: a / b if b != 0 else None,
}

TRIG_FUNCTIONS = {
    '8': 'sin',
    '9': 'cos',
    '10': 'tan',
    '11': 'arcsin',
    '12': 'arccos',
    '13': 'arctan',
}


def get_number(prompt):
    try:
        return float(input(prompt))
    except ValueError:
        print("Invalid input. Please enter a valid number.")
        return None


def calc_derivative():
    expr_str = input("Enter expression (e.g., x^2 + 3*x): ").replace('^', '**')
    x = sympy.Symbol('x')
    try:
        result = sympy.diff(sympy.sympify(expr_str), x)
        print(f"The derivative of {expr_str} with respect to x is: {result}")
    except sympy.SympifyError as e:
        print(f"Invalid input. Ensure expression is valid. Error: {e}")


def calc_integral():
    parts = [p.strip() for p in input("Enter expression and integration limits (e.g., x^2, 0, 1): ").split(',')]
    if len(parts) != 3:
        print("Invalid input format. Please enter expression, lower limit, and upper limit separated by commas (e.g., x^2, 0, 1).")
        return
    expr_str = parts[0].replace('^', '**')
    try:
        lower, upper = float(parts[1]), float(parts[2])
        x = sympy.Symbol('x')
        integral = sympy.integrate(sympy.sympify(expr_str), (x, lower, upper))
        print(f"The definite integral is: {integral}")
    except (sympy.SympifyError, ValueError) as e:
        print(f"Invalid input. Ensure expression is valid and limits are numbers. Error: {e}")


MENU = {
    '1': 'Addition (+)',
    '2': 'Subtraction (-)',
    '3': 'Multiplication (*)',
    '4': 'Division (/)',
    '5': 'Derivative Calculator',
    '6': 'Exponent Calculator (^)',
    '7': 'Integral Calculator',
    '8': 'Sine (sin)',
    '9': 'Cosine (cos)',
    '10': 'Tangent (tan)',
    '11': 'Arcsine (asin)',
    '12': 'Arccosine (acos)',
    '13': 'Arctangent (atan)',
    '14': 'Quit',
}


while True:
    print("\nSelect operation:")
    for key, label in MENU.items():
        print(f"{key}. {label}")

    choice = input("Enter choice: ")

    if choice == '14':
        print("Exiting calculator.")
        break

    if choice == '5':
        calc_derivative()
    elif choice == '7':
        calc_integral()
    elif choice == '6':
        base = get_number("Enter base number: ")
        exponent = get_number("Enter exponent: ")
        if base is not None and exponent is not None:
            print(f"The result is: {base ** exponent}")
    elif choice in OPERATIONS:
        num1 = get_number("Enter first number: ")
        num2 = get_number("Enter second number: ")
        if num1 is not None and num2 is not None:
            result = OPERATIONS[choice](num1, num2)
            if result is not None:
                print(f"The result is: {result}")
            else:
                print("Error: Division by zero.")
    elif choice in TRIG_FUNCTIONS:
        func = TRIG_FUNCTIONS[choice]
        x = get_number(f"Enter value for {func}(): ")
        if x is not None:
            try:
                print(f"The result is: {func(x)}")
            except ValueError as e:
                print(f"Error: {e}")
    else:
        print("Invalid choice. Please enter a number between 1 and 14.")
