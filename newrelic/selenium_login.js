/**
 * ReliBank Selenium Login Script
 * This script opens the ReliBank application and performs a login
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Navigate to ReliBank login page
$browser.get('http://relibank.westus2.cloudapp.azure.com/').then(function(){
  console.log('Navigated to ReliBank homepage');

  // Wait for the login page to load and find the username field
  return $browser.findElement($driver.By.id('username')).then(function(usernameField){
    console.log('Found username field');

    // Enter username
    return usernameField.sendKeys('demo').then(function(){
      console.log('Entered username: demo');

      // Find and fill in the password field
      return $browser.findElement($driver.By.id('password')).then(function(passwordField){
        console.log('Found password field');

        return passwordField.sendKeys('password').then(function(){
          console.log('Entered password');

          // Find and click the Sign In button
          return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(submitButton){
            console.log('Found submit button');

            return submitButton.click().then(function(){
              console.log('Clicked Sign In button');

              // Wait for navigation to complete and verify we're logged in
              return $browser.wait($driver.until.urlContains('dashboard'), 10000).then(function(){
                console.log('Successfully logged in - redirected to dashboard');

                // Verify we're on the dashboard by checking the URL
                return $browser.getCurrentUrl().then(function(url){
                  assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
                  console.log('Login successful! Current URL: ' + url);
                });
              });
            });
          });
        });
      });
    });
  });
}).catch(function(error){
  console.error('Login failed with error:', error);
  throw error;
});
