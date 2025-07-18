import argparse
from users import delete_user

def main():
    parser = argparse.ArgumentParser(description="Delete a user from the database by email")
    parser.add_argument('--email', type=str, required=True, help='Email of the user to delete')
    args = parser.parse_args()

    deleted_count = delete_user(args.email)
    if deleted_count > 0:
        print(f"✅ Successfully deleted user with email: {args.email}")
    else:
        print(f"⚠️ No user found with email: {args.email}")

if __name__ == '__main__':
    main()