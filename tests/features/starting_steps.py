from lettuce import *
import la


world.output = []  # One list element per printed line

def mock_output(s):
    world.output.append(s)

@before.all
def setup_mock_output():
    la.output = mock_output


def run_la(cmd):
    args = cmd.split(' ')
    la.main(args)


@step('la is uninitialized')
def given_that_la_is_uninitialized(step):
    assert True, 'The database for la has not been created yet'


@step('When I run la without parameters')
def when_i_run_la_without_parameters(step):
    la.main()


@step('I see error uninitialized')
def then_i_see_error_uninitialized(step):
    status = 'La has not been initialized.'
    assert world.output[-2] == status


@step('advice to initialize')
def advice_to_initialize(step):
    advice = 'Run la --init'
    assert world.output[-1] == advice


@step('la is initialized')
def given_that_la_is_initialized(step):
    assert True, 'The database for la is setup.'


@step('I create a tag called me')
def when_i_create_a_tag_called_me(step):
    cmd = 'create tag me'
    run_la(cmd)



@step('I list all my tags')
def and_i_list_all_my_tags(step):
    cmd = 'ls'
    run_la(cmd)


@step('I see (\d+) tag with id (\d+) and name (.+)')
def then_i_see_1_tag_with_id_1_and_name_me(step, nr_tags, id, name):
    expected = '%s tag %s' % (id, name)
    result = world.output[-1]
    print('expected:' + expected)
    print(result)
    print('now assert')
    assert expected == result
