# Reddit API functionalities

From time to time, I delete and switch to a new reddit account.
Deleting all posts manually is impossible, so this script exists.
There are also browser extensions for this, but they are harder to trust and might be abandoned randomly.
The reddit API will be around.

To transfer to a new user, the main steps are:

1. Get API access for old account
2. Edit (to nonsense) and delete all posts and submissions of old account
3. Get list of subscribed subreddits of old account
4. Create new account
5. Subscribe to previous subreddits there

Steps 1 and 4 are not scriptable, those need to be completed manually on the web.
Step 2 is currently available as a script, so is step 3.
Step 5 I had done manually.

The current approach is garbage.
It only works with the old account's API, but it would be much better to work with *both*,
old *and* new, accounts' APIs simultaneously.
Instead of fetching the old account's API access info from the CLI or interactively,
we would read it, together with the new account's info, from a file.
Then, create two `reddit` API instances and work with them in tandem, instead of only
the old one.
This would allow for the old subreddit subscriptions to be directly transferred by
[subscribing](https://praw.readthedocs.io/en/latest/code_overview/models/subreddit.html#praw.models.Subreddit.subscribe)
to them via the API using the *new* account.
The new order would then be:

1. Get API access for old account
2. Create new account and also set up API access
3. Edit (to nonsense) and delete all posts and submissions of old account
4. Subscribe to all subreddits of old account on new account
5. Maybe more stuff

Steps 1 and 2 would be quick and manual, the rest would be automated.
I've now completed transferring accounts, so can't be arsed to implement that now.
Maybe next year.
