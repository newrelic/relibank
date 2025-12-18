/**
 * ReliBank Selenium Login and Transfer Script
 * This script opens the ReliBank application, logs in, and performs a funds transfer
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

    // Wait for the login page to load and find the Sign In button
    const submitButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found submit button on login page');

    // Click Sign In button without entering credentials (form has default values)
    await submitButton.click();
    console.log('Clicked Sign In button');

    // Wait for navigation to complete and verify we're logged in
    await $browser.wait($driver.until.urlContains('dashboard'), 10000);
    console.log('Successfully logged in - redirected to dashboard');

    // Verify we're on the dashboard
    const url = await $browser.getCurrentUrl();
    assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
    console.log('Login successful! Current URL: ' + url);

    // Wait for the Transfer Funds card to load
    await $browser.wait($driver.until.elementLocated($driver.By.css('input[type="number"]')), 5000);
    console.log('Transfer form loaded');

    // Find and enter transfer amount
    const amountField = await $browser.findElement($driver.By.css('input[type="number"]'));
    console.log('Found amount field');

    await amountField.sendKeys('100');
    console.log('Entered transfer amount: $100');

    // Find the "From" dropdown
    const fromSelect = await $browser.findElement($driver.By.id('from-account-select'));
    console.log('Found from account dropdown');

    // Click to open dropdown and select checking
    await fromSelect.click();
    console.log('Opened from account dropdown');

    // Wait a moment for dropdown to open
    await $browser.sleep(500);

    // Find and click "checking" option in the dropdown
    const checkingOption = await $browser.findElement($driver.By.css('li[data-value="checking"]'));
    await checkingOption.click();
    console.log('Selected checking as from account');

    // Find the "To" dropdown
    const toSelect = await $browser.findElement($driver.By.id('to-account-select'));
    console.log('Found to account dropdown');

    // Click to open dropdown
    await toSelect.click();
    console.log('Opened to account dropdown');

    // Wait a moment for dropdown to open
    await $browser.sleep(500);

    // Find and click "savings" option
    const savingsOption = await $browser.findElement($driver.By.css('li[data-value="savings"]'));
    await savingsOption.click();
    console.log('Selected savings as to account');

    // Find and click the Complete Transfer button
    const transferButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found Complete Transfer button');

    await transferButton.click();
    console.log('Clicked Complete Transfer button');

    // Wait for success message to appear
    await $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000);
    console.log('Transfer completed - success message appeared');

    // Verify the success message
    const alertMessage = await $browser.findElement($driver.By.css('.MuiAlert-message'));
    const text = await alertMessage.getText();
    assert.ok(text.includes('Successfully transferred'), 'Success message should confirm transfer');
    console.log('Transfer successful! Message: ' + text);

    // Wait a moment before clicking other buttons
    await $browser.sleep(1000);

    // Click the "Show All" button in transactions if it exists
    const showAllButtons = await $browser.findElements($driver.By.xpath("//button[contains(text(), 'Show All')]"));
    if (showAllButtons.length > 0) {
      console.log('Found Show All transactions button');
      await showAllButtons[0].click();
      console.log('Clicked Show All transactions button');
      await $browser.sleep(500);
    } else {
      console.log('Show All button not found, skipping');
    }

    // Click the "Show Less" button if it exists
    const showLessButtons = await $browser.findElements($driver.By.xpath("//button[contains(text(), 'Show Less')]"));
    if (showLessButtons.length > 0) {
      console.log('Found Show Less transactions button');
      await showLessButtons[0].click();
      console.log('Clicked Show Less transactions button');
      await $browser.sleep(500);
    } else {
      console.log('Show Less button not found, skipping');
    }

    // Now transfer the funds back to checking
    console.log('Starting reverse transfer back to checking');

    // Scroll back to the transfer form
    const amountField2 = await $browser.findElement($driver.By.css('input[type="number"]'));
    console.log('Found amount field for reverse transfer');

    // Clear and enter the same amount
    await amountField2.clear();
    await amountField2.sendKeys('100');
    console.log('Entered reverse transfer amount: $100');

    // Find the "From" dropdown and select savings
    const fromSelect2 = await $browser.findElement($driver.By.id('from-account-select'));
    console.log('Found from account dropdown for reverse transfer');

    await fromSelect2.click();
    console.log('Opened from account dropdown');

    await $browser.sleep(500);

    // Select savings as from account
    const savingsOption2 = await $browser.findElement($driver.By.css('li[data-value="savings"]'));
    await savingsOption2.click();
    console.log('Selected savings as from account');

    // Wait for the dropdown to close before clicking the next one
    await $browser.sleep(1000);

    // Find the "To" dropdown and select checking
    const toSelect2 = await $browser.findElement($driver.By.id('to-account-select'));
    console.log('Found to account dropdown');

    await toSelect2.click();
    console.log('Opened to account dropdown');

    await $browser.sleep(500);

    // Select checking as to account
    const checkingOption2 = await $browser.findElement($driver.By.css('li[data-value="checking"]'));
    await checkingOption2.click();
    console.log('Selected checking as to account');

    // Click the Complete Transfer button again
    const transferButton2 = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found Complete Transfer button for reverse transfer');

    await transferButton2.click();
    console.log('Clicked Complete Transfer button for reverse transfer');

    // Wait for success message and allow telemetry to be sent
    console.log('Waiting 2 seconds for reverse transfer to complete and telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Reverse transfer completed');

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait of 2 seconds for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed!');

  } catch (error) {
    console.error('Script failed with error:', error);
    throw error;
  }
})();
