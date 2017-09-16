Feature: Organize tags
  In order to organize stuff
  We wish to apply tags to items and other tags


  Scenario: Add a parent tag to a tag
      Given I have 2 tags aa, bb
      When I tag bb with aa
      And I list all my tags
      Then I see that aa is a parent of bb

  Scenario: Remove a parent tag from a tag
      Given I have 2 tags aa, bb
      And aa is a parent of bb
      When I untag aa from bb
      And I list all my tags
      Then I see 2 tags with names aa and bb

  Scenario: Cannot tag itself as a parent

  Scenario: Cannot tag itself as an ancenstor

  Scenario: Deleting a used tag gives a warning

  Scenario: Can add multiple tags

  Scenario: Create a tag and add multiple tags at once
