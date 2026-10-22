#!/bin/sh
# git credential helper. hands git the token from a 600 file so the token
# never ends up in .git/config, in a url, or on the command line.
# git calls this with "get" and reads the two lines from stdout.
case "$1" in
  get)
    echo "username=x-access-token"
    echo "password=$(cat "$HOME/.hermes/mia/secrets/github_token")"
    ;;
  store|erase)
    ;;
esac
