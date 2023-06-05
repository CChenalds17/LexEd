import openai
import asyncio
import PySimpleGUI as sg

async def loading_bar(window: sg.Window = None, key: str ='-ERR_MSG-'):
    if window == None:
        return
    while True:
        window[key].update('Loading.', text_color='white')
        window.Refresh()
        await asyncio.sleep(0.3)
        window[key].update('Loading..', text_color='white')
        window.Refresh()
        await asyncio.sleep(0.3)
        window[key].update('Loading...', text_color='white')
        window.Refresh()
        await asyncio.sleep(0.3)

async def call_openai(model_name: str, init_prompt: str, prompt: str, temp=1, max_tok=200, window=None, key='-ERR_MSG-') -> tuple[str, str]:
    '''
    Utility function to call ChatGPT/GPT4 while handling exceptions.\n
    Takes in model_name, init_prompt, prompt, temp, max_tok, window, key; returns (out_msg, err_instr).
    '''
    out_msg = ''
    err_instr = ''

    try:
        loading_task = asyncio.create_task(loading_bar(window=window, key=key))
        # If no init_prompt:
        if init_prompt == '':
            m = [{"role": "user", "content": prompt}]
            output = await openai.ChatCompletion.acreate(
                        model = model_name,
                        messages = [
                            {"role": "user", "content": prompt}
                        ],
                        temperature = temp,
                        max_tokens = max_tok,
                        top_p = 0
                    )
            loading_task.cancel()
            out_msg = output['choices'][0]['message']['content']
        # If yes init_prompt:
        else:
            m = [{"role": "system", "content": init_prompt},{"role": "user", "content": prompt}]
            output = await openai.ChatCompletion.acreate(
                        model = model_name,
                        messages = [
                            {"role": "system", "content": init_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature = temp,
                        max_tokens = max_tok,
                        top_p = 0
                    )
            loading_task.cancel()
            out_msg = output['choices'][0]['message']['content']
    except openai.error.Timeout as e:
        out_msg = ''
        err_instr = 'Request timed out. Please try again in a bit.'
    except openai.error.APIError as e:
        out_msg = ''
        err_instr = 'There is a problem with OpenAI. Please try again in a bit.'
    except openai.error.APIConnectionError as e:
        out_msg = ''
        err_instr = 'Failed to connect to OpenAI. Please check your network settings or firewall rules and try again.'
    except openai.error.InvalidRequestError as e:
        out_msg = ''
        err_instr = 'Request was invalid. Please try again with a different input.'
    except openai.error.AuthenticationError as e:
        out_msg = ''
        err_instr = 'API key invalid or expired. Please enter a valid API key.'
    except openai.error.PermissionError as e:
        out_msg = ''
        err_instr = 'Request not permitted. Please make sure your API key has permissions for gpt-3.5-turbo and gpt-4.'
    except openai.error.RateLimitError as e:
        out_msg = ''
        err_instr = 'Request exceeded rate limit. Please wait a minute and try again.'
    except openai.error.ServiceUnavailableError as e:
        out_msg = ''
        err_instr = 'There is a problem with OpenAI. Please try again in a bit.'
    except Exception as e:
        out_msg = ''
        err_inistr = e
    finally:
        if window != None:
                window[key].update('')
                window.Refresh()

    return (out_msg, err_instr)

async def verify_key(api_key: str, window=None, key='-ERR_MSG-') -> tuple[bool, str]:
    '''
    Verifies OpenAI API Key. If exception is thrown, returns error info and user instructions.\n
    Takes in api_key, window, key; returns (is_valid_key, err_instr).
    '''
    is_valid_key = None
    openai.api_key = api_key

    (out_msg, err_instr) = await call_openai('gpt-3.5-turbo', '', 'Hi', max_tok=1, window=window, key=key)

    # If no exceptions:
    if err_instr == '':
        is_valid_key = True
    # If yes exceptions:
    else:
        is_valid_key = False

    return (is_valid_key, err_instr)

async def is_correct(text: str, window=None, key='-ERR_MSG-') -> tuple[bool, str]:
    '''
    Checks if the text contains errors.\n
    Takes in text, window, key; returns (is_correct, err_instr).
    '''
    is_correct = None

    is_correct_init_prompt = "You are a helpful AI assistant."
    is_correct_prompt = f"Is the following grammatically correct? Just tell me yes or no, nothing else.\n\n\"{text}\""
    (out_msg, err_instr) = await call_openai('gpt-3.5-turbo', is_correct_init_prompt, is_correct_prompt, window=window, key=key)

    # If no exceptions:
    if err_instr == '':
        is_correct = out_msg.lower()[0] == 'y'
    # If yes exceptions:
    else:
        is_correct = False
    
    return (is_correct, err_instr)

async def correct(text: str, window=None, key='-ERR_MSG-') -> tuple[str, str]:
    '''
    Corrects text.\n
    Takes in text, window, key; returns (corrected, err_instr).
    '''
    corrected = ''
    
    correct_prompt = f"Check the following for spelling and grammatical errors. Just return the corrected text, nothing else.\n\n\"{text}\""
    (out_msg, err_instr) = await call_openai('gpt-3.5-turbo', '', correct_prompt, window=window, key=key)

    corrected = out_msg.strip().strip('"')
    return (corrected, err_instr)

async def explain_error(sent_A: str, sent_B: str, window=None, key='-ERR_MSG-') -> tuple[str, str]:
    '''
    Explains the grammatical error between sent_A (incorrect) and sent_B (correct).\n
    Takes in sent_A, sent_B, window, key; returns (explanation, err_instr).
    '''
    explanation = ''

    expl_error_init_prompt = "You are SmartTutor, an AI designed to help non-native English speakers improve their professional English. Please be comprehensive but concise in your answers."
    expl_error_prompt = f"Sentence B is the grammatically corrected version of sentence A. Given every difference, which sentence B corrects, comprehensively explain why sentence A needs to be changed, using understandable everyday language. Precede this with a short, easy to remember description of the errors, or error, followed by a newline break. Keep the explanation under or as close to 20 words as possible per error.\n\nA: {sent_A}\nB: {sent_B}"
    
    (out_msg, err_instr) = await call_openai('gpt-3.5-turbo', expl_error_init_prompt, expl_error_prompt, window=window, key=key)

    explanation = out_msg
    return (explanation, err_instr)

async def gen_incorrect(sent_A: str, window=None, key='-ERR_MSG-') -> tuple[str, str]:
    '''
    Generates a sentece with the same grammatical error as sent_A.\n
    Takes in sent_A, window, key; returns (sent_B, err_instr).
    '''
    sent_B = ''

    gen_incorrect_prompt = f"Generate a sentence with the same grammatical error as sentence A\n\nA: Your child were at school today\nB: She were eating dinner\n\nA: The dogs were eat at the park\nB: The children were sit at the table\n\nA: We need to get our sale's numbers up\nB: There are many desk's in this room\n\nA: {sent_A}\nB:"
    (out_msg, err_instr) = await call_openai('gpt-4', '', gen_incorrect_prompt, window=window, key=key)

    sent_B = out_msg
    return (sent_B, err_instr)

async def gen_correct(sent_A: str, window=None, key='-ERR_MSG-') -> tuple[str, str]:
    '''
    Generates a grammatically corrrect sentence with the same grammar concept that sent_A got wrong.\n
    Takes in sent_A, window, key; returns (sent_B, err_instr).
    '''
    sent_B = ''

    gen_correct_init_prompt = "You are a helpful AI assistant."
    gen_correct_prompt = f"Generate a grammatically correct sentence using the grammar concept that the following sentence uses incorrectly, but change the subject. Just give me the sentence, nothing else.\n\n\"{sent_A}\""
    (out_msg, err_instr) = await call_openai('gpt-4', gen_correct_init_prompt, gen_correct_prompt, window=window, key=key)

    sent_B = out_msg
    return (sent_B, err_instr)

async def check(text: str, window=None, key='-ERR_MSG-') -> tuple[list[str], list[str], str]:
    '''
    Checks text for grammatical errors.\n
    Takes in text, window, key; returns (errors[], corrected[], err_instr).
    '''
    errors = []
    corrected = []
    err_instr = ''

    # Check if the text even contains grammatical errors
    (no_errors, err_instr) = await is_correct(text, window=window, key=key)
    # If there's an exception, just return empty lists & err_instr
    if err_instr != '':
        return (errors, corrected, err_instr)
    # If there are no grammatical errors, return empty lists & empty err_instr
    if no_errors:
        return (errors, corrected, err_instr)
    
    check_init_prompt = "You are a helpful AI assistant."
    check_prompt_1 = f"List the grammatically incorrect sentence, or sentences, each separated by the '|' character. Nothing else. If there is only one, just return the sentence.\n\n\"{text}\""
    # If there are grammatical errors, call ChatGPT to find them
    (out_msg_1, err_instr) = await call_openai('gpt-3.5-turbo', check_init_prompt, check_prompt_1, window=window, key=key)
    if err_instr != '':
        return (errors, corrected, err_instr)
    check_prompt_2 = f"Correct each sentence, separating each with the '|' character. If there is only one, just return the corrected sentence.\n\n\"{out_msg_1}\""
    (out_msg2, err_instr) = await call_openai('gpt-3.5-turbo', check_init_prompt, check_prompt_2, window=window, key=key)
    if err_instr != '':
        return (errors, corrected, err_instr)
    
    e = out_msg_1.strip().strip('"').split('|')
    c = out_msg2.strip().strip('"').split('|')

    for i in range(0, len(e)):
        errors.append(e[i].strip())
        corrected.append(c[i].strip())
    for i in range(0, len(errors)):
        if errors[i] == corrected[i]:
            del errors[i]
            del corrected[i]

    return (errors, corrected, err_instr)
