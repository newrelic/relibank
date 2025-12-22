/**
 * ReliBank Selenium Login Script
 * This script opens the ReliBank application and performs a login
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Main async function
(async function() {
  try {
    // Navigate to ReliBank login page
    await $browser.get('http://relibank.westus2.cloudapp.azure.com/');
    console.log('Navigated to ReliBank homepage');

    // Wait for the login page to load and find the username field
    const usernameField = await $browser.findElement($driver.By.id('username'));
    console.log('Found username field');

    // Enter username
    await usernameField.sendKeys('demo');
    console.log('Entered username: demo');

    // Find and fill in the password field
    const passwordField = await $browser.findElement($driver.By.id('password'));
    console.log('Found password field');

    await passwordField.sendKeys('password');
    console.log('Entered password');

    // Find and click the Sign In button
    const submitButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found submit button');

    await submitButton.click();
    console.log('Clicked Sign In button');

    // Wait for navigation to complete and verify we're logged in
    await $browser.wait($driver.until.urlContains('dashboard'), 10000);
    console.log('Successfully logged in - redirected to dashboard');

    // Verify we're on the dashboard by checking the URL
    const url = await $browser.getCurrentUrl();
    assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
    console.log('Login successful! Current URL: ' + url);

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait of 2 seconds for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed!');

  } catch (error) {
    console.error('Login failed with error:', error);
    throw error;
  }
})();
