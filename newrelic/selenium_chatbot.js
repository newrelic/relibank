/**
 * ReliBank Selenium Insufficient Funds and Support Script
 * This script tests the scenario where a user:
 * 1. Logs in
 * 2. Attempts to transfer more money than available in their account
 * 3. Receives an insufficient funds error
 * 4. Navigates to support
 * 5. Submits a question about why the transfer didn't go through
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Navigate to ReliBank login page
$browser.get('http://relibank.westus2.cloudapp.azure.com/').then(function(){
  console.log('Navigated to ReliBank homepage');

  // Wait for the login page to load and find the Sign In button
  return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(submitButton){
    console.log('Found submit button on login page');

    // Click Sign In button without entering credentials (form has default values)
    return submitButton.click().then(function(){
      console.log('Clicked Sign In button');

      // Wait for navigation to complete and verify we're logged in
      return $browser.wait($driver.until.urlContains('dashboard'), 10000).then(function(){
        console.log('Successfully logged in - redirected to dashboard');

        // Verify we're on the dashboard
        return $browser.getCurrentUrl().then(function(url){
          assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
          console.log('Login successful! Current URL: ' + url);

          // Wait for the Transfer Funds card to load
          return $browser.wait($driver.until.elementLocated($driver.By.css('input[type="number"]')), 5000).then(function(){
            console.log('Transfer form loaded');

            // Find and enter transfer amount (more than checking account balance of $8,500.25)
            return $browser.findElement($driver.By.css('input[type="number"]')).then(function(amountField){
              console.log('Found amount field');

              return amountField.sendKeys('10000').then(function(){
                console.log('Entered transfer amount: $10,000 (exceeds checking balance of $8,500.25)');

                // Find the "From" dropdown
                return $browser.findElement($driver.By.id('from-account-select')).then(function(fromSelect){
                  console.log('Found from account dropdown');

                  // Click to open dropdown and select checking
                  return fromSelect.click().then(function(){
                    console.log('Opened from account dropdown');

                    // Wait a moment for dropdown to open
                    return $browser.sleep(500).then(function(){

                      // Find and click "checking" option in the dropdown
                      return $browser.findElement($driver.By.css('li[data-value="checking"]')).then(function(checkingOption){
                        return checkingOption.click().then(function(){
                          console.log('Selected checking as from account');

                          // Find the "To" dropdown
                          return $browser.findElement($driver.By.id('to-account-select')).then(function(toSelect){
                            console.log('Found to account dropdown');

                            // Click to open dropdown
                            return toSelect.click().then(function(){
                              console.log('Opened to account dropdown');

                              // Wait a moment for dropdown to open
                              return $browser.sleep(500).then(function(){

                                // Find and click "savings" option
                                return $browser.findElement($driver.By.css('li[data-value="savings"]')).then(function(savingsOption){
                                  return savingsOption.click().then(function(){
                                    console.log('Selected savings as to account');

                                    // Find and click the Complete Transfer button
                                    return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(transferButton){
                                      console.log('Found Complete Transfer button');

                                      return transferButton.click().then(function(){
                                        console.log('Clicked Complete Transfer button');

                                        // Wait for error message to appear
                                        return $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000).then(function(){
                                          console.log('Transfer failed - error message appeared');

                                          // Verify the error message
                                          return $browser.findElement($driver.By.css('.MuiAlert-message')).then(function(alertMessage){
                                            return alertMessage.getText().then(function(text){
                                              assert.ok(text.includes('Insufficient funds'), 'Error message should indicate insufficient funds');
                                              console.log('Transfer failed as expected! Message: ' + text);

                                              // Now navigate to Support
                                              console.log('Navigating to Support page to submit a question');

                                              return $browser.findElement($driver.By.css('a[href="/support"]')).then(function(supportLink){
                                                return supportLink.click().then(function(){
                                                  console.log('Clicked Support link');

                                                  // Wait for support page to load
                                                  return $browser.wait($driver.until.urlContains('support'), 5000).then(function(){
                                                    console.log('Successfully navigated to support page');

                                                    // Wait for the chat input field to load
                                                    return $browser.wait($driver.until.elementLocated($driver.By.css('input[type="text"]')), 5000).then(function(){
                                                      console.log('Support chat loaded');

                                                      // Find the message input field
                                                      return $browser.findElement($driver.By.css('input[type="text"]')).then(function(messageField){
                                                        console.log('Found message input field');

                                                        // Type the support question
                                                        var supportMessage = 'Why did my transfer not go through? I tried to transfer $10,000 from checking to savings but got an error.';
                                                        return messageField.sendKeys(supportMessage).then(function(){
                                                          console.log('Typed support message: ' + supportMessage);

                                                          // Find and click the Send button
                                                          return $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]')).then(function(sendButton){
                                                            console.log('Found Send button');

                                                            return sendButton.click().then(function(){
                                                              console.log('Clicked Send button - support message submitted');

                                                              // Wait a moment to see if the message appears in the chat
                                                              return $browser.sleep(1000).then(function(){
                                                                console.log('Support scenario completed successfully!');
                                                                console.log('Summary: Login -> Insufficient funds transfer -> Support question submitted');
                                                              });
                                                            });
                                                          });
                                                        });
                                                      });
                                                    });
                                                  });
                                                });
                                              });
                                            });
                                          });
                                        });
                                      });
                                    });
                                  });
                                });
                              });
                            });
                          });
                        });
                      });
                    });
                  });
                });
              });
            });
          });
        });
      });
    });
  });
}).catch(function(error){
  console.error('Script failed with error:', error);
  throw error;
});
