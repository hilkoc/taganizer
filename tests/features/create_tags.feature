Feature: Create tags
  In order to organize stuff
  We wish to be able to tag anything
  Using our tool called la.

  Scenario: Show status
    Given la is uninitialized
    When I run la without parameters
    Then I see error uninitialized
    And advice to initialize

  Scenario: Cannot do anything if uninitialized
    Given la is uninitialized
    When I create a tag called me
    Then I see error uninitialized
    And advice to initialize

  Scenario: Create a tag
      Given that la is initialized
      When I create a tag called aa
      And I list all my tags
      Then I see 1 tag with name aa

  Scenario: List all tags
      Given I have 2 tags aa, bb
      When I list all my tags
      Then I see 2 tags with names aa and bb

  Scenario: Delete a tag
      Given I have 2 tags aa, bb
      When I delete bb
      And I list all my tags
      Then I see 1 tag with name aa

  Scenario: Rename a tag
      Given I have 2 tags aa, bb
      When I rename bb to cc
      And I list all my tags
      Then I see 2 tags with names aa and cc
