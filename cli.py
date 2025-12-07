#!/usr/bin/env python3
"""
Command Line Interface for Israeli Lottery Predictor
"""
import sys
from database import LotteryDatabase, initialize_database
from predictor import LotteryPredictor
from datetime import datetime


def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("🎱 Israeli Lottery Predictor CLI")
    print("=" * 60)
    print()


def print_menu():
    """Print main menu."""
    print("\nMain Menu:")
    print("1. Initialize/Import Database from CSV")
    print("2. Generate Predictions")
    print("3. View Statistics")
    print("4. Add New Result")
    print("5. View Recent Results")
    print("6. Exit")
    print()


def initialize_db():
    """Initialize database from CSV."""
    print("\n[Initializing Database]")
    print("-" * 60)
    
    csv_file = input("Enter CSV filename (default: Lotto.csv): ").strip()
    if not csv_file:
        csv_file = "Lotto.csv"
    
    try:
        imported, skipped = initialize_database(csv_file)
        print(f"\n✓ Database initialized successfully!")
        print(f"  - Imported: {imported} records")
        print(f"  - Skipped: {skipped} records")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def generate_predictions():
    """Generate lottery predictions."""
    print("\n[Generate Predictions]")
    print("-" * 60)
    
    try:
        num_predictions = int(input("Number of predictions (1-10, default: 5): ") or "5")
        num_predictions = max(1, min(10, num_predictions))
    except ValueError:
        num_predictions = 5
    
    print(f"\nGenerating {num_predictions} predictions...\n")
    
    predictor = LotteryPredictor()
    predictor.connect()
    
    predictions = predictor.generate_predictions(num_predictions)
    
    for pred in predictions:
        print(f"Prediction #{pred['prediction_number']}")
        print(f"  Strategy: {pred['strategy']}")
        print(f"  Numbers: {' '.join([f'[{n:02d}]' for n in pred['numbers']])}")
        print(f"  Strong Number: [{pred['strong_number']}]")
        print()
    
    predictor.close()


def view_statistics():
    """View lottery statistics."""
    print("\n[Statistics]")
    print("-" * 60)
    
    predictor = LotteryPredictor()
    predictor.connect()
    
    stats = predictor.get_statistics()
    
    print(f"\nTotal Draws: {stats['total_draws']}")
    print(f"\nMost Common Number: {stats['most_common_number'][0]} (appeared {stats['most_common_number'][1]} times)")
    print(f"Least Common Number: {stats['least_common_number'][0]} (appeared {stats['least_common_number'][1]} times)")
    print(f"\nMost Common Strong Number: {stats['most_common_strong'][0]} (appeared {stats['most_common_strong'][1]} times)")
    print(f"Least Common Strong Number: {stats['least_common_strong'][0]} (appeared {stats['least_common_strong'][1]} times)")
    
    print(f"\nHot Numbers (Recent 50 draws): {stats['hot_numbers']}")
    print(f"Cold Numbers (Recent 50 draws): {stats['cold_numbers']}")
    print(f"Overdue Numbers: {stats['overdue_numbers']}")
    
    predictor.close()


def add_result():
    """Add a new lottery result."""
    print("\n[Add New Result]")
    print("-" * 60)
    
    db = LotteryDatabase()
    db.connect()
    
    # Get next draw number
    latest_draw = db.get_latest_draw_number()
    next_draw = (latest_draw + 1) if latest_draw else 1
    
    try:
        draw_number = int(input(f"Draw Number (suggested: {next_draw}): ") or str(next_draw))
        draw_date = input("Draw Date (DD/MM/YYYY, or press Enter for today): ").strip()
        
        if not draw_date:
            draw_date = datetime.now().strftime("%d/%m/%Y")
        
        print("\nEnter the 6 main numbers (1-37):")
        numbers = []
        for i in range(1, 7):
            while True:
                try:
                    num = int(input(f"  Number {i}: "))
                    if 1 <= num <= 37:
                        numbers.append(num)
                        break
                    else:
                        print("    Number must be between 1 and 37")
                except ValueError:
                    print("    Please enter a valid number")
        
        while True:
            try:
                strong_number = int(input("\nStrong Number (1-7): "))
                if 1 <= strong_number <= 7:
                    break
                else:
                    print("  Strong number must be between 1 and 7")
            except ValueError:
                print("  Please enter a valid number")
        
        success = db.add_result(draw_number, draw_date, numbers, strong_number)
        
        if success:
            print("\n✓ Result added successfully!")
        else:
            print("\n✗ Failed to add result")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    db.close()


def view_recent_results():
    """View recent lottery results."""
    print("\n[Recent Results]")
    print("-" * 60)
    
    try:
        limit = int(input("Number of results to show (default: 10): ") or "10")
    except ValueError:
        limit = 10
    
    db = LotteryDatabase()
    db.connect()
    
    results = db.get_latest_results(limit)
    
    print(f"\nShowing {len(results)} most recent results:\n")
    print(f"{'Draw #':<8} {'Date':<12} {'Numbers':<40} {'Strong'}")
    print("-" * 70)
    
    for result in results:
        draw_num, date, n1, n2, n3, n4, n5, n6, strong = result
        numbers_str = f"{n1:02d} {n2:02d} {n3:02d} {n4:02d} {n5:02d} {n6:02d}"
        print(f"{draw_num:<8} {date:<12} {numbers_str:<40} {strong}")
    
    db.close()


def main():
    """Main CLI function."""
    print_banner()
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            initialize_db()
        elif choice == '2':
            generate_predictions()
        elif choice == '3':
            view_statistics()
        elif choice == '4':
            add_result()
        elif choice == '5':
            view_recent_results()
        elif choice == '6':
            print("\nThank you for using Israeli Lottery Predictor!")
            print("Good luck! 🍀")
            sys.exit(0)
        else:
            print("\n✗ Invalid choice. Please enter 1-6.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting... Goodbye! 👋")
        sys.exit(0)


