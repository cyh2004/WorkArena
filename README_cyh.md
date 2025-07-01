## Getting Started

To setup WorkArena, you will need to get your own ServiceNow instance, install our Python package, and upload some data to your instance. Follow the steps below to achieve this.

### a) Create a ServiceNow Developer Instance

1. Go to https://developer.servicenow.com/ and create an account.
2. Click on `Request an instance` and select the `Washington` release (initializing the instance will take a few minutes)
3. Once the instance is ready, you should see your instance URL and credentials. If not, click _Return to the Developer Portal_, then navigate to _Manage instance password_ and click _Reset instance password_.
4. You should now see your URL and credentials. Based on this information, set the following environment variables:
    * `SNOW_INSTANCE_URL`: The URL of your ServiceNow developer instance
    * `SNOW_INSTANCE_UNAME`: The username, should be "admin"
    * `SNOW_INSTANCE_PWD`: The password, make sure you place the value in quotes "" and be mindful of [escaping special shell characters](https://onlinelinuxtools.com/escape-shell-characters). Running `echo $SNOW_INSTANCE_PWD` should print the correct password.
6. Log into your instance via a browser using the admin credentials. Close any popup that appears on the main screen (e.g., agreeing to analytics).

**Warning:** Feel free to look around the platform, but please make sure you revert any changes (e.g., changes to list views, pinning some menus, etc.) as these changes will be persistent and affect the benchmarking process.

### b) Install WorkArena and Initialize your Instance

Run the following command to install WorkArena in the [BrowswerGym](https://github.com/servicenow/browsergym) environment:
```
pip install browsergym
```

Then install local code (in 'src' folder) into environment
```
pip install -e .
```

Then, install [Playwright](https://github.com/microsoft/playwright):
```
playwright install
```

Finally, run this command in a terminal to upload the benchmark data to your ServiceNow instance:
```
workarena-install
```
Your installation is now complete! 🎉

