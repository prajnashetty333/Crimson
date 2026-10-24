#!/usr/bin/env python3
"""
OvaCare Moderator Management CLI
Safely provisions and audits moderator privileges without exposing public registration endpoints.
"""

import sys
import os
import argparse

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from db import execute_query, execute_write

def list_moderators():
    mods = execute_query(
        "SELECT user_id, username, email, role FROM users WHERE role IN ('moderator', 'admin')"
    )
    if not mods:
        print("No users currently have moderator or admin privileges.")
        return
    print(f"\n{'USER ID':<20} | {'USERNAME':<20} | {'ROLE':<10} | {'EMAIL'}")
    print("-" * 75)
    for m in mods:
        print(f"{m['user_id']:<20} | {m['username']:<20} | {m.get('role', 'member'):<10} | {m['email']}")
    print(f"\nTotal moderators/admins: {len(mods)}\n")

def promote_user(email, role='moderator'):
    users = execute_query("SELECT user_id, username, email, role FROM users WHERE email = :email", {"email": email})
    if not users:
        print(f"Error: User with email '{email}' does not exist.")
        sys.exit(1)
        
    u = users[0]
    execute_write("UPDATE users SET role = :role WHERE user_id = :uid", {"role": role, "uid": u['user_id']})
    print(f"Success: User '{u['username']}' ({email}) has been granted '{role}' privileges.")

def demote_user(email):
    users = execute_query("SELECT user_id, username, email, role FROM users WHERE email = :email", {"email": email})
    if not users:
        print(f"Error: User with email '{email}' does not exist.")
        sys.exit(1)
        
    u = users[0]
    execute_write("UPDATE users SET role = 'member' WHERE user_id = :uid", {"uid": u['user_id']})
    print(f"Success: Privileges removed. User '{u['username']}' ({email}) role is now 'member'.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OvaCare Moderator Provisioning CLI")
    parser.add_argument("--list", action="store_true", help="List all users with moderator/admin roles.")
    parser.add_argument("--promote", type=str, metavar="EMAIL", help="Promote a user email to moderator.")
    parser.add_argument("--demote", type=str, metavar="EMAIL", help="Demote a user email to regular member.")
    parser.add_argument("--role", type=str, default="moderator", choices=["moderator", "admin"], help="Role to assign (default: moderator).")
    
    args = parser.parse_args()
    
    if args.list:
        list_moderators()
    elif args.promote:
        promote_user(args.promote, role=args.role)
    elif args.demote:
        demote_user(args.demote)
    else:
        parser.print_help()
