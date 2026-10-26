
use std::io;

/// Formats a number like Python's `f"${x:,.2f}"` — e.g. 12345.678 -> "$12,345.68".
fn format_money(x: f64) -> String {
    let mut s = format!("{:.2}", x);
    let neg = s.starts_with('-');
    if neg {
        s = s.trim_start_matches('-').to_string();
    }
    let whole = s.split('.').next().unwrap_or(&s);
    let cents = s.split('.').nth(1).unwrap_or("00");
    let digits = whole.chars().collect::<String>();
    let len = digits.len();
    let mut result = String::new();
    for (i, c) in digits.chars().enumerate() {
        result.push(c);
        let remaining = len - i - 1;
        if remaining % 3 == 0 && remaining > 0 {
            result.push(',');
        }
    }
    let result = if neg { format!("-${result}") } else { result };
    format!("${result}.{cents}")
}

fn mortgage_payment(principal: f64, annual_rate: f64, years: i64) -> f64 {
    if annual_rate <= 0.0 {
        return principal / (years as f64 * 12.0);
    }
    let monthly_rate = annual_rate / 12.0;
    let n = years as f64 * 12.0;
    principal * monthly_rate / (1.0 - (1.0 + monthly_rate).powf(-n))
}

fn mortgage_total_interest(principal: f64, annual_rate: f64, years: i64) -> f64 {
    let payment = mortgage_payment(principal, annual_rate, years);
    payment * years as f64 * 12.0 - principal
}

fn mortgage_payoff_months(principal: f64, annual_rate: f64) -> u64 {
    let mut balance = principal;
    let mut months = 0u64;
    if annual_rate <= 0.0 {
        // Direct translation of the original Python's odd branch:
        // max(1, math.ceil(principal / (principal / (principal / 1))))
        return std::cmp::max(1, principal.ceil() as u64);
    }
    let monthly_rate = annual_rate / 12.0;
    let payment = mortgage_payment(principal, annual_rate, 30);
    while balance > 0.01 && months < 100_000 {
        let interest = balance * monthly_rate;
        balance -= payment - interest;
        if balance < 0.0 {
            balance = 0.0;
        }
        months += 1;
    }
    months
}

fn mortgage_total_cost(principal: f64, annual_rate: f64, years: i64) -> f64 {
    mortgage_payment(principal, annual_rate, years) * years as f64 * 12.0
}

fn rent_annual(monthly_rent: f64) -> f64 {
    monthly_rent * 12.0
}

fn rent_weekly(monthly_rent: f64) -> f64 {
    (monthly_rent / 52.0 * 100.0).round() / 100.0
}

const MENU: &[(&str, &str)] = &[
    ("1", "Mortgage: monthly payment"),
    ("2", "Mortgage: total interest paid"),
    ("3", "Mortgage: months to pay off"),
    ("4", "Rent: annual cost"),
    ("5", "Rent: weekly cost"),
    ("6", "Rent vs. Buy: monthly comparison"),
    ("7", "Rent vs. Buy: annual savings"),
    ("8", "Quit"),
];

fn get_money(prompt: &str) -> Option<f64> {
    print!("{prompt}");
    let mut input = String::new();
    let parsed = match io::stdin().read_line(&mut input) {
        Ok(_) => input.trim().parse::<f64>().ok(),
        Err(_) => None,
    };
    if parsed.is_none() {
        println!("Invalid input. Please enter a valid number.");
    }
    parsed
}

fn get_number(prompt: &str) -> Option<i64> {
    print!("{prompt}");
    let mut input = String::new();
    let parsed = match io::stdin().read_line(&mut input) {
        Ok(_) => input.trim().parse::<i64>().ok(),
        Err(_) => None,
    };
    if parsed.is_none() {
        println!("Invalid input. Please enter a whole number.");
    }
    parsed
}

fn calc_mortgage(principal: f64, annual_rate: f64, years: i64) {
    println!("Principal: ${}", format_money(principal));
    println!("Annual rate: {}%", annual_rate);
    println!("Term: {} years", years);
    println!("{}", "-".repeat(40));
    println!(
        "Monthly payment: ${}",
        format_money(mortgage_payment(principal, annual_rate, years))
    );
    println!(
        "Total interest paid: ${}",
        format_money(mortgage_total_interest(principal, annual_rate, years))
    );
    println!(
        "Total cost (principal + interest): ${}",
        format_money(mortgage_total_cost(principal, annual_rate, years))
    );
    println!(
        "Months to pay off: {}",
        mortgage_payoff_months(principal, annual_rate)
    );
}

fn calc_rent(monthly_rent: f64) {
    println!("Monthly rent: ${}", format_money(monthly_rent));
    println!("{}", "-".repeat(40));
    println!(
        "Annual rent cost: ${}",
        format_money(rent_annual(monthly_rent))
    );
    println!(
        "Weekly rent cost: ${}",
        format_money(rent_weekly(monthly_rent))
    );
}

fn calc_rent_vs_buy(monthly_rent: f64, principal: f64, annual_rate: f64, years: i64) {
    let monthly_payment = mortgage_payment(principal, annual_rate, years);
    println!("Rent vs. Buy comparison");
    println!("{}", "-".repeat(40));
    println!("Monthly rent:    ${}", format_money(monthly_rent));
    println!("Monthly payment: ${}", format_money(monthly_payment));
    println!("{}", "-".repeat(40));
    if monthly_rent > monthly_payment {
        println!(
            "You pay ${}",
            format_money(monthly_rent - monthly_payment)
        );
    } else if monthly_rent < monthly_payment {
        println!(
            "You save ${}",
            format_money(monthly_payment - monthly_rent)
        );
    } else {
        println!("Same cost per month either way!");
    }
    println!("Annual rent:  ${}", format_money(rent_annual(monthly_rent)));
    println!("Annual cost:  ${}", format_money(monthly_payment * 12.0));
}

fn calc_savings(monthly_rent: f64, principal: f64, annual_rate: f64, years: i64) {
    let monthly_payment = mortgage_payment(principal, annual_rate, years);
    let annual_rent = rent_annual(monthly_rent);
    let annual_buy = monthly_payment * 12.0;
    println!("Annual Rent vs. Buy comparison");
    println!("{}", "-".repeat(40));
    println!("Annual rent:  ${}", format_money(annual_rent));
    println!("Annual cost:  ${}", format_money(annual_buy));
    println!("{}", "-".repeat(40));
    if annual_rent > annual_buy {
        println!("Renting costs ${}", format_money(annual_rent - annual_buy));
    } else if annual_rent < annual_buy {
        println!("Renting saves you ${}", format_money(annual_buy - annual_rent));
    } else {
        println!("Same cost per year either way!");
    }
}

fn option_mortgage() {
    let principal = get_money("Enter mortgage principal (loan amount): ");
    let rate = get_money("Enter annual interest rate (e.g., 6.5 for 6.5%): ");
    let years = get_number("Enter loan term in years: ");
    if principal.is_some() && rate.is_some() && years.is_some() && years.unwrap() > 0 {
        calc_mortgage(principal.unwrap(), rate.unwrap() / 100.0, years.unwrap());
    }
}

fn option_total_interest() {
    let principal = get_money("Enter mortgage principal (loan amount): ");
    let rate = get_money("Enter annual interest rate (e.g., 6.5 for 6.5%): ");
    let years = get_number("Enter loan term in years: ");
    if principal.is_some() && rate.is_some() && years.is_some() && years.unwrap() > 0 {
        println!(
            "Total interest paid: ${}",
            format_money(
                mortgage_total_interest(principal.unwrap(), rate.unwrap() / 100.0, years.unwrap())
            )
        );
    }
}

fn option_payoff() {
    let principal = get_money("Enter mortgage principal (loan amount): ");
    let rate = get_money("Enter annual interest rate (e.g., 6.5 for 6.5%): ");
    if principal.is_some() && rate.is_some() {
        println!(
            "Months to pay off: {}",
            mortgage_payoff_months(principal.unwrap(), rate.unwrap() / 100.0)
        );
    }
}

fn option_rent_annual() {
    let rent = get_money("Enter monthly rent: ");
    if rent.is_some() {
        println!("Annual rent cost: ${}", format_money(rent_annual(rent.unwrap())));
    }
}

fn option_rent_weekly() {
    let rent = get_money("Enter monthly rent: ");
    if rent.is_some() {
        println!("Weekly rent cost: ${}", format_money(rent_weekly(rent.unwrap())));
    }
}

fn option_rent_vs_buy() {
    let rent = get_money("Enter monthly rent: ");
    let principal = get_money("Enter mortgage principal (loan amount): ");
    let rate = get_money("Enter annual interest rate (e.g., 6.5 for 6.5%): ");
    let years = get_number("Enter loan term in years: ");
    if rent.is_some()
        && principal.is_some()
        && rate.is_some()
        && years.is_some()
        && years.unwrap() > 0
    {
        calc_rent_vs_buy(
            rent.unwrap(),
            principal.unwrap(),
            rate.unwrap() / 100.0,
            years.unwrap(),
        );
    }
}

fn option_savings() {
    let rent = get_money("Enter monthly rent: ");
    let principal = get_money("Enter mortgage principal (loan amount): ");
    let rate = get_money("Enter annual interest rate (e.g., 6.5 for 6.5%): ");
    let years = get_number("Enter loan term in years: ");
    if rent.is_some()
        && principal.is_some()
        && rate.is_some()
        && years.is_some()
        && years.unwrap() > 0
    {
        calc_savings(rent.unwrap(), principal.unwrap(), rate.unwrap() / 100.0, years.unwrap());
    }
}

fn main() {
    loop {
        println!("\nSelect option:");
        for (key, label) in MENU {
            println!("{key}. {label}");
        }
        print!("Enter choice: ");
        let mut choice = String::new();
        match io::stdin().read_line(&mut choice) {
            Ok(_) => {}
            Err(_) => break,
        }
        match choice.trim() {
            "8" => {
                println!("Exiting. Good luck with the house hunt!");
                break;
            }
            "1" => option_mortgage(),
            "2" => option_total_interest(),
            "3" => option_payoff(),
            "4" => option_rent_annual(),
            "5" => option_rent_weekly(),
            "6" => option_rent_vs_buy(),
            "7" => option_savings(),
            _ => println!("Invalid choice. Please enter a number between 1 and 8."),
        }
    }
}
