import PySimpleGUI as sg
import gpt_tester
import random
import os
import json
import base64
import asyncio
from typing import Tuple, List

with open('resources/icon.ico', 'rb') as file:
    icon = file.read()
sg.set_global_icon(base64.b64encode(icon))

default_font = sg.DEFAULT_FONT

# ~ Function to build intro window ~ #
async def build_intro(change_api_key=False) -> bool:
    '''
    Builds the intro window (for users to input API Keys).\n
    Returns is_valid_key
    '''

    is_valid_key = False 
    init_err_msg = ''
    OPENAI_PROB_ERR_MSGS = ['Request timed out. Please try again in a bit.', 'There is a problem with OpenAI. Please try again in a bit.', 
                            'Failed to connect to OpenAI. Please check your network settings or firewall rules and try again.', 'Request was invalid. Please try again with a different input.',
                            'Request exceeded rate limit. Please wait a minute and try again.', 'There is a problem with OpenAI. Please try again in a bit.']

    # If first time launching app and 'credentials.json' exists and API keys are valid, return True
    if os.path.isfile('credentials.json') and not change_api_key:
        with open('credentials.json', 'r') as credentials:
            try:
                creds_dict = json.load(credentials)
                openai_api_key = base64.b64decode(creds_dict['OPENAI_API_KEY'].encode()).decode()
                verify_key_task = asyncio.create_task(gpt_tester.verify_key(openai_api_key))
                try:
                    (is_valid_key, err_instr) = await verify_key_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                # If exception:
                if err_instr != '':
                    # Set error message and then show prompt API key window
                    init_err_msg = err_instr
                # If no exception:
                else:
                    if is_valid_key:
                        return is_valid_key #True
                        # And then build SmartTutor
            # In case there's an error opening/parsing credentials.json
            except Exception as e:
                is_valid_key = False
                init_err_msg = 'There was an error loading your OpenAI API key. Please enter it again.'
            
    # Layout
    intro_layout = [
        [sg.Text('Please input your API Key below:'), sg.Push(), sg.Button('Use current API Key', visible=change_api_key or init_err_msg in OPENAI_PROB_ERR_MSGS)],
        [sg.Text('OpenAI API Key:'), sg.Input('', password_char='*', enable_events=True, focus=True, key='-OPENAI_API_KEY-')],
        [sg.Button('Submit', disabled=True), sg.Push(), sg.Text(init_err_msg, size=(40, None), text_color='dark orange', key='-ERR_MSG-'), sg.Push(), sg.Exit()]
    ]
    
    window = sg.Window(title='LexEd', layout=intro_layout, font=default_font, resizable=False, finalize=True)

    # Main loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            is_valid_key = False
            break

        # If API key is filled out, make 'Submit' button clickable
        if event == '-OPENAI_API_KEY-':
            if window['-OPENAI_API_KEY-'].get() != '':
                window['Submit'].update(disabled=False)
        
        # 'Submit' button: Verify API keys
        if event == 'Submit':

            # Verify key
            verify_key_task = asyncio.create_task(gpt_tester.verify_key(window['-OPENAI_API_KEY-'].get(), window=window))
            try:
                (is_valid_key, err_instr) = await verify_key_task
            except asyncio.CancelledError:
                err_instr = "An error has occurred. Please try again."

            # If error, display error then go to beginning of loop:
            if err_instr != '':
                window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                continue
            window['-ERR_MSG-'].update('')

            # If key is valid, store key in 'credentials.json' (as base64 str)
            if is_valid_key:
                with open('credentials.json', 'w') as credentials:
                    openai_api_key_b64 = base64.b64encode(window['-OPENAI_API_KEY-'].get().encode()).decode()
                    json.dump({"OPENAI_API_KEY": openai_api_key_b64}, credentials)
                break
                # And then build SmartTutor
            # If key is invalid, display error and have user try again
            else:
                window['-ERR_MSG-'].update(err_instr, text_color='dark orange')

        if event == 'Use current API Key':
            is_valid_key = True
            break
                
    window.close()
    
    # If key is valid and this came here from settings, build_SmartTutor(). Once SmartTutor() is legitimately exited, return False and break the loop/nest.
    if is_valid_key and change_api_key:
        await build_SmartTutor()
        return False
    # If key isn't valid and/or is first launch, return is_valid_key. Will either go to build_SmartTutor() (if key is valid) or exit app (if key isn't valid)
    else:
        return is_valid_key

# ~ Function to build Practice window ~ #
async def build_practice(errors_in: List[str], base_window: sg.Window) -> None:
    '''
    Builds the practice exercises window.\n
    Takes in errors_in[], base_window; returns nothing.\n
    Loops through list of errors and generates a similarly grammatically incorrect sentence for each error.
    '''

    errors = []
    example_sents = []
    recurring_errors = []
    cycling_again_flag = False
    end_of_curr_cycle_flag = False

    for error in errors_in:
        errors.append((error, False))
        example_sents.append(error)

    # Adds random grammatically correct sentences to the pool (either 1 + 1/3 of len(errors) or 10, whichever is smaller)
    for i in range(0, len(errors) // 3 + 1):
        errors.append(('', True))
    random.shuffle(errors)

    error_num = 0
    init_err_msg = ''

    # Generating a correct sentence
    if errors[error_num][1]:
        sent_idx = random.randint(0, len(example_sents)-1)
        gen_correct_task = asyncio.create_task(gpt_tester.gen_correct(example_sents[sent_idx], base_window))
        try:
            (curr_exercise, err_instr) = await gen_correct_task
        except asyncio.CancelledError:
            err_instr = "An error has occurred. Please try again."
        # If error, display error (then build screen as normal)
        if err_instr != '':
            init_err_msg = err_instr
        # If no error, remove example sentence from example_sents[]
        else:
            del example_sents[sent_idx]
    # Generating an incorrect sentence
    else:
        gen_incorrect_task = asyncio.create_task(gpt_tester.gen_incorrect(errors[error_num][0], base_window))
        try:
            (curr_exercise, err_instr) = await gen_incorrect_task
        except asyncio.CancelledError:
            err_instr = "An error has occurred. Please try again."
        if err_instr != '':
            init_err_msg = err_instr

    # Updates errors[] with sentence (to be accessed while explaining)
    errors[error_num] = (curr_exercise, errors[error_num][1])

    p_correct = 0
    p_incorrect = 0
    p_remaining = len(errors)

    # Screen layout
    practice_layout = [
        [sg.Push(), sg.Text(f'Is this sentence grammatically correct?', key='-P_INFO-', font=(default_font[0], default_font[1]+1, 'bold')), sg.Push()],
        [sg.Push(), sg.Text('A:'), sg.Text(curr_exercise, key='-CURR_EXER-'), sg.Push()],
        [sg.Push(), sg.Col([[sg.Text('B:', visible=False, key='B'), sg.Input('', size=30, visible=False, key='-IN-'), sg.Submit('Check', visible=False)]], pad=(0,0)), sg.Push()],
        [sg.Push(), sg.Col([[sg.Button('Correct'), sg.Button('Incorrect')], [sg.VPush()]], pad=(0,0)), sg.Push()],
        [sg.Push(), sg.Text('', justification='center', key='-RESULT-'), sg.Push()],
        [sg.Push(), sg.Text('', justification='center', key='-ANSWER-'), sg.Push()],
        [sg.VPush()],
        [sg.Multiline('', size=(55, 4), disabled=True, text_color='white', background_color='SlateGray', key='-EXPLANATION-')],
        [sg.VPush()],
        [sg.Push(), sg.Text(p_remaining, text_color='yellow', key='-P_REM-'), sg.Text(p_correct, text_color='light green', key='-P_CORR-'), sg.Text(p_incorrect, text_color='red', key='-P_INCORR-')],
        [sg.Text(init_err_msg, size=(40, 2), justification='left', text_color='dark orange', key='-ERR_MSG-'), sg.Push(), sg.Button('Next', disabled=True), sg.Exit(visible=False)]
    ]

    window = sg.Window(title='Practice', layout=practice_layout, font=default_font, modal=True, resizable=False)

    # Main loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        if event == 'Incorrect':
            # If user is correct ('Incorrect' and generated incorrect):
            if not errors[error_num][1]:
                window['B'].update(visible=True)
                window['-IN-'].update(visible=True)
                window['Correct'].update(visible=False)
                window['Incorrect'].update(visible=False)
                window['Check'].update(visible=True)
                window['-P_INFO-'].update('Please correct the sentence.')
            # If user is incorrect ('Incorrect' but generated correct):
            else:
                # Make 'Incorrect' and 'Correct' unclickable
                window['Correct'].update(disabled=True)
                window['Incorrect'].update(disabled=True)
                # Show answer
                window['-RESULT-'].update('Incorrect', text_color='red')
                window['-ERR_MSG-'].update('')
                # Display correct sentence
                window['-ANSWER-'].update('This sentence is already correct.', text_color='light green')
                if errors:
                    recurring_errors.append(errors[error_num])
                # If last exercise, reset errors[] and error_num to cycle through incorrect problems
                if error_num == len(errors) - 1:
                    random.shuffle(recurring_errors)
                    errors = recurring_errors
                    recurring_errors = []
                    error_num = -1
                    # If there were no more incorrect problems, make 'Next' button unclickable & invisible; make 'Exit' visible
                    if not errors:
                        window['Next'].update(disabled=True, visible=False)
                        window['Exit'].update(visible=True)
                    else:
                        window['Next'].update(disabled=False)
                        end_of_curr_cycle_flag = True
                # If there is another exercise, make 'Next' button clickable
                else:
                    window['Next'].update(disabled=False)
                # Make '-IN-' field intangible (until next exercise)
                window['-IN-'].update(disabled=True)
                if not cycling_again_flag:
                    p_incorrect += 1
                    p_remaining -= 1
                if end_of_curr_cycle_flag:
                    cycling_again_flag = end_of_curr_cycle_flag
                    end_of_curr_cycle_flag = False
                window['-P_REM-'].update(p_remaining)
                window['-P_CORR-'].update(p_correct)
                window['-P_INCORR-'].update(p_incorrect)
        elif event == 'Correct':
            # Makes 'Incorrect' and 'Correct' buttons unclickable
            window['Correct'].update(disabled=True)
            window['Incorrect'].update(disabled=True)
            # If user is correct ('Correct' and generated correct):
            if errors[error_num][1]:
                window['-ERR_MSG-'].update('')
                # Update '-RESULT-' text
                window['-RESULT-'].update('Correct!', text_color='light green')
                window['-ANSWER-'].update('This sentence is already correct.', text_color='light green')
                # If last exercise, reset errors[] and error_num to cycle through incorrect problems
                if error_num == len(errors) - 1:
                    random.shuffle(recurring_errors)
                    errors = recurring_errors
                    recurring_errors = []
                    error_num = -1
                    # If there were no more incorrect problems, make 'Next' button unclickable & invisible; make 'Exit' visible
                    if not errors:
                        window['Next'].update(disabled=True, visible=False)
                        window['Exit'].update(visible=True)
                    else:
                        window['Next'].update(disabled=False)
                        end_of_curr_cycle_flag = True
                # If there is another exercise, make 'Next' button clickable
                else:
                    window['Next'].update(disabled=False)
                # Make '-IN-' field intangible (until next exercise)
                window['-IN-'].update(disabled=True)
                p_correct += 1
                if cycling_again_flag:
                    p_incorrect -= 1
                else:
                    p_remaining -= 1
                if end_of_curr_cycle_flag:
                    cycling_again_flag = end_of_curr_cycle_flag
                    end_of_curr_cycle_flag = False
            # If user is incorrect ('Correct' but generated incorrect):
            else:
                # Make '-IN-' field intangible (until next exercise)
                window['-IN-'].update(disabled=True)
                # Show answer
                window['-RESULT-'].update('Incorrect', text_color='red')
                # Generate correct sentence
                correct_task = asyncio.create_task(gpt_tester.correct(errors[error_num][0], window=window))
                try:
                    (corr_sent, err_instr) = await correct_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                # If error, display error message then go back to beginning of loop:
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Makes 'Incorrect' and 'Correct' buttons clickable
                    window['Correct'].update(disabled=False)
                    window['Incorrect'].update(disabled=False)
                    # Make '-IN-' field tangible
                    window['-IN-'].update(disabled=False)
                    continue
                window['-ERR_MSG-'].update('')
                # Display correct sentence
                window['-ANSWER-'].update(corr_sent, text_color='light green')
                # Explain
                explain_error_task = asyncio.create_task(gpt_tester.explain_error(errors[error_num][0], window['-ANSWER-'].get(), window=window))
                try:
                    (explanation, err_instr) = await explain_error_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Makes 'Incorrect' and 'Correct' buttons clickable
                    window['Correct'].update(disabled=False)
                    window['Incorrect'].update(disabled=False)
                    # Make '-IN-' field tangible
                    window['-IN-'].update(disabled=False)
                    continue
                window['-ERR_MSG-'].update('')
                # Displays explanation
                window['-EXPLANATION-'].update(explanation)
                if errors:
                    recurring_errors.append(errors[error_num])
                # If last exercise, reset errors[] and error_num to cycle through incorrect problems
                if error_num == len(errors) - 1:
                    random.shuffle(recurring_errors)
                    errors = recurring_errors
                    recurring_errors = []
                    error_num = -1
                    # If there were no more incorrect problems, make 'Next' button unclickable & invisible; make 'Exit' visible
                    if not errors:
                        window['Next'].update(disabled=True, visible=False)
                        window['Exit'].update(visible=True)
                    else:
                        window['Next'].update(disabled=False)
                        end_of_curr_cycle_flag = True
                # If there is another exercise, make 'Next' button clickable
                else:
                    window['Next'].update(disabled=False)
                if not cycling_again_flag:
                    p_incorrect += 1
                    p_remaining -= 1
                if end_of_curr_cycle_flag:
                    cycling_again_flag = end_of_curr_cycle_flag
                    end_of_curr_cycle_flag = False
            window['-P_REM-'].update(p_remaining)
            window['-P_CORR-'].update(p_correct)
            window['-P_INCORR-'].update(p_incorrect)

        # 'Check' button: Checks user answer (only clickable when supposed to)
        if event == 'Check':
            # If '-IN-' is empty or 'Check' button is invisible, don't do anything
            if window['-IN-'].get() == '' or not window['Check'].visible:
                continue
            else:
                # Make '-IN-' field intangible (until next exercise)
                window['-IN-'].update(disabled=True)
                # Make 'Check' button unclickable (until user hits 'Next')
                window['Check'].update(disabled=True)
                is_correct_task = asyncio.create_task(gpt_tester.is_correct(window['-IN-'].get(), window=window))
                try:
                    (is_correct, err_instr) = await is_correct_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                # If error, display error message then go back to beginning of loop:
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Make '-IN-' field tangible
                    window['-IN-'].update(disabled=False)
                    # Make 'Check' button clickable
                    window['Check'].update(disabled=False)
                    continue
                window['-ERR_MSG-'].update('')

            # If user is incorrect
            if not is_correct:
                # Show answer
                window['-RESULT-'].update('Incorrect', text_color='red')
                # Generates the correct sentence
                correct_task = asyncio.create_task(gpt_tester.correct(errors[error_num][0], window=window))
                try:
                    (corr_sent, err_instr) = await correct_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                # If error, display error message then go back to beginning of loop:
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Make '-IN-' field tangible
                    window['-IN-'].update(disabled=False)
                    # Make 'Check' button clickable
                    window['Check'].update(disabled=False)
                    continue
                window['-ERR_MSG-'].update('')
                # Displays correct sentence
                window['-ANSWER-'].update(corr_sent, text_color='light green')
                # Explain
                explain_error_task = asyncio.create_task(gpt_tester.explain_error(window['-IN-'].get(), window['-ANSWER-'].get(), window=window))
                try: 
                    (explanation, err_instr) = await explain_error_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Make '-IN-' field tangible
                    window['-IN-'].update(disabled=False)
                    # Make 'Check' button clickable
                    window['Check'].update(disabled=False)
                    continue
                window['-ERR_MSG-'].update('')
                # Displays explanation
                window['-EXPLANATION-'].update(explanation)
                if errors:
                    recurring_errors.append(errors[error_num])
                # If last exercise, reset errors[] and error_num to cycle through incorrect problems
                if error_num == len(errors) - 1:
                    random.shuffle(recurring_errors)
                    errors = recurring_errors
                    recurring_errors = []
                    error_num = -1
                    # If there were no more incorrect problems, make 'Next' button unclickable & invisible; make 'Exit' visible
                    if not errors:
                        window['Next'].update(disabled=True, visible=False)
                        window['Exit'].update(visible=True)
                    else:
                        window['Next'].update(disabled=False)
                        end_of_curr_cycle_flag = True
                # If there is another exercise, make 'Next' button clickable
                else:
                    window['Next'].update(disabled=False)
                if not cycling_again_flag:
                    p_incorrect += 1
                    p_remaining -= 1
                if end_of_curr_cycle_flag:
                    cycling_again_flag = end_of_curr_cycle_flag
                    end_of_curr_cycle_flag = False
            # If user is correct (generated correct & checked '-NO_ERROR-'; generated incorrect & submitted correct)
            else:
                window['-ERR_MSG-'].update('')
                # Update '-RESULT-' text
                window['-RESULT-'].update('Correct!', text_color='light green')
                # If last exercise, reset errors[] and error_num to cycle through incorrect problems
                if error_num == len(errors) - 1:
                    random.shuffle(recurring_errors)
                    errors = recurring_errors
                    recurring_errors = []
                    error_num = -1
                    # If there were no more incorrect problems, make 'Next' button unclickable & invisible; make 'Exit' visible
                    if not errors:
                        window['Next'].update(disabled=True, visible=False)
                        window['Exit'].update(visible=True)
                    else:
                        window['Next'].update(disabled=False)
                        end_of_curr_cycle_flag = True
                # If there is another exercise, make 'Next' button clickable
                else:
                    window['Next'].update(disabled=False)
                p_correct += 1
                if cycling_again_flag:
                    p_incorrect -= 1
                else:
                    p_remaining -= 1
                if end_of_curr_cycle_flag:
                    cycling_again_flag = end_of_curr_cycle_flag
                    end_of_curr_cycle_flag = False
            window['-P_REM-'].update(p_remaining)
            window['-P_CORR-'].update(p_correct)
            window['-P_INCORR-'].update(p_incorrect)
        
        # 'Next' button: Cycles to next exercise (only clickable when supposed to)
        if event == 'Next':
            # Make 'Next' button unclickable (until user hits 'Check')
            window['Next'].update(disabled=True)
            # Make '-IN-' input intangible
            window['-IN-'].update(disabled=True)
            # Display next exercise (if there is one)
            # If next sentence is correct, generates a correct sentence
            if errors[error_num+1][1]:
                if not cycling_again_flag:
                    sent_idx = random.randint(0, len(example_sents)-1)
                    gen_correct_task = asyncio.create_task(gpt_tester.gen_correct(example_sents[sent_idx], window=window))
                else:
                    gen_correct_task = asyncio.create_task(gpt_tester.gen_correct(errors[error_num+1][0], window=window))
                try:
                    (curr_exercise, err_instr) = await gen_correct_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                # If error, display error (then build screen as normal)
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Make 'Next' button clickable
                    window['Next'].update(disabled=False)
                    # Make '-IN-' input intangible
                    window['-IN-'].update(disabled=False)
                    continue
                # If no error & first time through, remove example sentence from example_sents[]
                elif not cycling_again_flag:
                    del example_sents[sent_idx]
            # If next sentence is incorrect, generates an incorrect sentence
            else:
                gen_incorrect_task = asyncio.create_task(gpt_tester.gen_incorrect(errors[error_num+1][0], window=window))
                try: 
                    (curr_exercise, err_instr) = await gen_incorrect_task
                except asyncio.CancelledError:
                    err_instr = "An error has occurred. Please try again."
                if err_instr != '':
                    window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                    # Make 'Next' button clickable
                    window['Next'].update(disabled=False)
                    # Make '-IN-' input intangible
                    window['-IN-'].update(disabled=False)
                    continue
                
            # Clear '-ANSWER-' text
            window['-ANSWER-'].update('')
            # Clears '-RESULT-' text
            window['-RESULT-'].update('')
            # Clear '-EXPLANAION-' text
            window['-EXPLANATION-'].update('')
            # Make 'Check' button clickable
            window['Check'].update(disabled=False)
            # Clears '-IN-' input and makes it tangible
            window['-IN-'].update('')
            window['-IN-'].update(disabled=False)
            # Update '-P_INFO-'
            window['-P_INFO-'].update('Does this sentence contain any grammatical errors?')
            # Make 'B' and '-IN-' invisible
            window['B'].update(visible=False)
            window['-IN-'].update(visible=False)
            # Make 'Incorrect' and 'Correct' visible  & clickable; make 'Check' invisible
            window['Correct'].update(visible=True, disabled=False)
            window['Incorrect'].update(visible=True, disabled=False)
            window['Check'].update(visible=False)

            window['-P_REM-'].update(p_remaining)
            window['-P_CORR-'].update(p_correct)
            window['-P_INCORR-'].update(p_incorrect)

            error_num += 1
            errors[error_num] = (curr_exercise, errors[error_num][1])
            window['-CURR_EXER-'].update(curr_exercise)            

    window.close()

# ~ Function to update which grammatical error is displayed ~ #
def update_error(errors: List[str], corrected: List[str], error_num: int) -> str:
    '''
    Function to update which grammatical error is displayed.\n
    Takes in errors[], corrected[], error_num; returns errors[error_num], corrected[error_num] (or 'No errors' message).
    '''
    # If errors exist
    if errors:
        # Sentence A: Grammatically incorrect
        # Sentence B: Grammatically correct
        sent_A = errors[error_num]
        sent_B = corrected[error_num]
        return f'Original: {sent_A}\nCorrected: {sent_B}'   
    # If no errors exist     
    else:
        return 'No errors! Good job :)'

def update_input_sample(text: List[str], err_num_to_highlight: int, window: sg.Window, multi_key: str) -> None:
    window[multi_key].update('')
    for i in range(0, len(text)):
        # If correct chunk, append chunk normally
        if i % 2 == 0:
            window[multi_key].update(text[i], append=True)
        # If incorrect chunk, check if should be highlighted, then append chunk in red (and highlighted, if desired)
        else:
            if i == 2*err_num_to_highlight+1:
                window[multi_key].update(text[i], text_color_for_value='red', background_color_for_value='khaki', append=True)
            else:
                window[multi_key].update(text[i], text_color_for_value='red', append=True)

# ~ Function to build Main window ~ #
async def build_SmartTutor():
    '''
    Builds the main window
    '''
    menu_def = [['Settings', ['Change API Key']]]
    change_api_key = False

    # Left column (for writing sample)
    text_input_column = [
        [sg.Text('Enter your writing sample below:')],
        [sg.Multiline('This sentence are grammatical incorrect.', size=(70, 20), enable_events=True, key='-WRITING_INPUT-')]
    ]

    # Right column (for displaying errors)
    errors_column = [
        [sg.Text('Corrections:', key='-C_INFO-'), sg.Button('<', disabled=True), sg.Button('>', disabled=True)],
        [sg.Multiline(size=(30, 7), disabled=True, key='-ERRORS-')],
        [sg.Button('Explain', disabled=True)],
        [sg.VPush()],
        [sg.Multiline('', background_color='SlateGray', size=(30, 10), disabled=True, key='-EXPLANATION-')]
    ]

    # Screen layout
    main_layout = [
        [sg.Menu(menu_def)],
        [sg.Column(text_input_column), sg.VSeparator(), sg.Column(errors_column, size=(250, 360), pad=(0,0))],
        [sg.Button('Check'), sg.VSeparator(), sg.Button('Practice', disabled=True), sg.Push(), sg.Text('', size=(70, 1), text_color='dark orange', key='-ERR_MSG-'), sg.Push(), sg.Exit()]
    ]

    window = sg.Window(title='LexEd', layout=main_layout, font=default_font, resizable=False)

    # List of errors[] and corrected[]
    errors, corrected = [], []
    # List of explanations
    explanations = []
    # Error number in the list (to keep track of through button presses)
    error_num = 0
    
    # Main loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        if event == 'Change API Key':
            change_api_key = True
            break
        
        # CHECK AND CORRECT

        # Makes 'Check' button clickable when '-WRITING_INPUT-' changes
        if event == '-WRITING_INPUT-':
            window['Check'].update(disabled = False)

        # 'Check' button: Check writing sample
        if event == 'Check':
            
            if '|' in window['-WRITING_INPUT-'].get():
                window['-ERR_MSG-'].update("Input cannot contain '|'", text_color='dark orange')
                continue
            # Make 'Check' button unclickable (until '-WRITING_INPUT-' is changed)
            window['Check'].update(disabled=True)
            # If 'Check' button is clicked, reset errors[], corrected[], and explanations[]
            check_task = asyncio.create_task(gpt_tester.check(window['-WRITING_INPUT-'].get(), window=window))
            try:
                (errors, corrected, err_instr) = await check_task
            except asyncio.CancelledError:
                err_instr = "An error has occurred. Please try again."
            if err_instr != '':
                window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                window['Check'].update(disabled=False)
                continue
            window['-ERR_MSG-'].update('')

            # Sets to first error in sample whenever 'Check' button is clicked
            error_num = 0
            # Updates correction number
            if errors:
                window['-C_INFO-'].update(f'Corrections ({error_num+1}/{len(errors)}):')
            else:
                window['-C_INFO-'].update('Corrections (0/0):')

            explanations = []
            temp_writing_input = window['-WRITING_INPUT-'].get()
            new_writing_input = []
            
            # Set new_writing_input[] as list of chunks [correct, incorrect, correct, incorrect, ... , correct] (for easily red-texting incorrect)
            for i in range(0, len(errors)):
                # start idx of error
                curr_err_idx = temp_writing_input.find(errors[i])
                # add correct stuff (before curr error)
                new_writing_input.append(temp_writing_input[:curr_err_idx])
                # sample now starts at the end of curr error
                temp_writing_input = temp_writing_input[curr_err_idx+len(errors[i]):]
                # add curr error (+ ' ')
                new_writing_input.append(errors[i])
            # add correct stuff (after last error)
            new_writing_input.append(temp_writing_input)
            update_input_sample(new_writing_input, error_num, window, '-WRITING_INPUT-')

            # I am. He are. I am. He are. He are. He are. He are. He are. He are.

            # Makes 'Practice' button clickable
            window['Practice'].update(disabled=False)

            # Makes explanations[] the same length as errors[]
            for error in errors:
                explanations.append('')
            # Makes 'Explain' button clickable if there are errors
            if errors:
                window['Explain'].update(disabled=False)
            else:
                window['Explain'].update(disabled=True)

            # Display corrected text
            updated_error = update_error(errors, corrected, error_num).split('\n')
            if len(updated_error) == 1:
                window['-ERRORS-'].update(updated_error[0])
            else:
                window['-ERRORS-'].update(f'{updated_error[0]}\n{updated_error[1]}')
            # Display correct explanation (if there are errors)
            if errors:
                window['-EXPLANATION-'].update(explanations[error_num])

            # If there is more than 1 error, let user cycle to next error
            if len(errors) > 1:
                window['>'].update(disabled=False)
            else:
                window['>'].update(disabled=True)

        # '<' button: Previous error (only clickable when supposed to)
        if event == '<':
            # Make '>' button clickable when going to previous error
            window['>'].update(disabled=False)
            # If second error, go to first error and then make '<' button unclickable
            if error_num == 1:
                error_num -= 1
                window['<'].update(disabled=True)
            # If greater than second error, go to previous error and make sure '<' button is clickable
            elif error_num > 1:
                error_num -= 1
                window['<'].update(disabled=False)
            # Highlight correct error in '-WRITING_INPUT-'
            update_input_sample(new_writing_input, error_num, window, '-WRITING_INPUT-')
            # Display correct correction number
            window['-C_INFO-'].update(f'Corrections ({error_num+1}/{len(errors)}):')
            # Display correct error
            updated_error = update_error(errors, corrected, error_num).split('\n')
            if len(updated_error) == 1:
                window['-ERRORS-'].update(updated_error[0])
            else:
                window['-ERRORS-'].update(f'{updated_error[0]}\n{updated_error[1]}')
            # If explanations[error_num] already exists, make 'Explain' button unclickable
            if explanations and explanations[error_num] != '':
                window['Explain'].update(disabled = True)
            # Elif explanations[error_num] is empty, make 'Explain' button clickable
            elif explanations and explanations[error_num] == '':
                window['Explain'].update(disabled = False)
            # Display correct explanation
            window['-EXPLANATION-'].update(explanations[error_num])
        # '>' button: Next error (only clickable when supposed to)
        if event == '>':
            # Make '<' button clickable when going to next error
            window['<'].update(disabled=False)
            # If second-to-last error, go to last error and then make '>' button unclickable
            if error_num == len(errors) - 2:
                error_num += 1
                window['>'].update(disabled=True)
            # If less than second-to-last error, go to next error and make sure '>' button is clickable
            elif error_num < len(errors) - 2:
                error_num += 1
                window['>'].update(disabled=False)
            # Highlight correct error in '-WRITING_INPUT-'
            update_input_sample(new_writing_input, error_num, window, '-WRITING_INPUT-')
            # Display correct correction number
            window['-C_INFO-'].update(f'Corrections ({error_num+1}/{len(errors)}):')
            # Display correct error
            updated_error = update_error(errors, corrected, error_num).split('\n')
            if len(updated_error) == 1:
                window['-ERRORS-'].update(updated_error[0])
            else:
                window['-ERRORS-'].update(f'{updated_error[0]}\n{updated_error[1]}')           
            # If explanations[error_num] already exists, make 'Explain' button unclickable
            if explanations and explanations[error_num] != '':
                window['Explain'].update(disabled = True)
            # Elif explanations[error_num] is empty, make 'Explain' button clickable
            elif explanations and explanations[error_num] == '':
                window['Explain'].update(disabled = False)
            # Display correct explanation
            window['-EXPLANATION-'].update(explanations[error_num])

        # EXPLAIN

        # 'Explain' button: Explain the grammatical error (only clickable when intended)
        if event == 'Explain':
            # If 'Explain' buttton is clicked, make it unclickable (until cycling to the next error)
            window['Explain'].update(disabled = True)
            # Generate explanation
            explain_error_task = asyncio.create_task(gpt_tester.explain_error(errors[error_num], corrected[error_num], window=window))
            try:
                (explanations[error_num], err_instr) = await explain_error_task
            except asyncio.CancelledError:
                err_instr = "An error has occurred. Please try again."
            # If error, display error and then go to beginning of loop
            if err_instr != '':
                window['-ERR_MSG-'].update(err_instr, text_color='dark orange')
                window['Explain'].update(disabled = False)
                continue
            window['-ERR_MSG-'].update('')
            window['-EXPLANATION-'].update(explanations[error_num], text_color='white')

        # EXERCISES

        # 'Practice' button: Start practice window (only clickable after checking)
        if event == 'Practice':
            await build_practice(errors, window)
            window['-ERR_MSG-'].update('')

    window.close()

    if change_api_key:
        await build_intro(change_api_key)

# ~ Main function ~ #
async def main():
    if await build_intro():
        await build_SmartTutor()

if __name__ == '__main__':
    asyncio.run(main())
