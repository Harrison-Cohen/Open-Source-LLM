import sympy

while True:
    print("\nSelect operation:")
    print("1. Addition (+)")
    print("2. Subtraction (-)")
    print("3. Multiplication (*)")
    print("4. Division (/)")
    print("5. Derivative Calculator")
    print("6. Exponent Calculator (^) ")
    print("7. Integral Calculator")
    print("8. Quit")

    choice = input("Enter choice (1-8): ")

    if choice == '8':
        print("Exiting calculator.")
        break

    if choice == '7':
        try:
            expression_str = input("Enter expression and integration limits (e.g., x^2, 0, 1): ")
            parts = [p.strip() for p in expression_str.split(',')]
            
            if len(parts) != 3:
                print("Invalid input format. Please enter expression, lower limit, and upper limit separated by commas (e.g., x^2, 0, 1).")
                continue
                
            expression_str_calc = parts[0]
            lower_bound = float(parts[1])
            upper_bound = float(parts[2])

            expression_str_calc = expression_str_calc.replace('^', '**')
            x = sympy.Symbol('x')
            expression = sympy.sympify(expression_str_calc)
            
            integral = sympy.integrate(expression, (x, lower_bound, upper_bound))
            print(f"The definite integral is: {integral}")

        except (sympy. SympifyError, NameError, ValueError) as e:
            print(f"Invalid input. Ensure expression is valid and limits are numbers. Error: {e}")
        continue

    if choice == '6':
        try:
            base = float(input("Enter base number: "))
            exponent = float(input("Enter exponent: "))
            result = base ** exponent
            print(f"The result is: {result}")
        except ValueError:
            print("Invalid input. Please enter valid numbers.")
        continue

    if choice == '5':
        try:
            expression_str = input("Enter expression (e.g., x**2 + 3*x): ")
            expression_str = expression_str.replace('^', '**')
            x = sympy.Symbol('x')
            expression = sympy.sympify(expression_str)
            
            derivative = sympy.diff(expression, x)
            print(f"The derivative of {expression_str} with respect to x is: {derivative}")
        except (sympy. SympifyError, NameError) as e:
            print(f"Invalid input. Ensure expression is valid. Error: {e}")
        continue

    if choice in ('1', '2', '3', '4'):
        try:
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
        except ValueError:
            print("Invalid input. Please enter valid numbers.")
            continue

        result = None
        if choice == '1':
            result = num1 + num2
        elif choice == '2':
            result = num1 - num2
        elif choice == '3':
            result = num1 * num2
        elif choice == '4':
            if num2 != 0:
                result = num1 / num2
            else:
                print("Error: Division by zero is not allowed.")
                continue

        if result is not None:
            print(f"The result is: {result}")
    else:
        print("Invalid choice. Please enter a number between 1 and 8.")
