from playwright.sync_api import ElementHandle

def select_option_by_coordinate(page, selector, target_value, use_text_content=False):
    if use_text_content:
        value = selector.evaluate("el => el.options[el.selectedIndex].textContent")
    else:
        value = selector.get_attribute("value")
    if value == target_value:
        selector.click(empty=True)
        return
    selector.click()
    if isinstance(selector, ElementHandle):
        ops = selector.query_selector_all("option")
    else:
        ops = selector.locator("option").all()
    nth = -1
    for op in ops:
        if use_text_content:
            value = op.text_content()
        else:
            value = op.evaluate("el => el.getAttribute('value')")

        if value == target_value:
            nth = ops.index(op)
            break
    if nth == -1:
        import pdb; pdb.set_trace()
    assert nth != -1, f"Could not find option {target_value}"

    fontSize = ops[nth].evaluate('el => {return getComputedStyle(el).fontSize;}')
    assert "px" in fontSize, f"Could not get font size for operator {target_value}"
    fontSize = int(fontSize.replace("px", ""))
    marginTop = ops[nth].evaluate('el => {return getComputedStyle(el).marginTop;}')
    assert "px" in marginTop, f"Could not get margin top for operator {target_value}"
    marginTop = int(marginTop.replace("px", ""))
    marginBottom = ops[nth].evaluate('el => {return getComputedStyle(el).marginBottom;}')
    assert "px" in marginBottom, f"Could not get margin bottom for operator {target_value}"
    marginBottom = int(marginBottom.replace("px", ""))
    paddingTop = ops[nth].evaluate('el => {return getComputedStyle(el).paddingTop;}')
    assert "px" in paddingTop, f"Could not get padding top for operator {target_value}"
    paddingTop = int(paddingTop.replace("px", ""))
    paddingBottom = ops[nth].evaluate('el => {return getComputedStyle(el).paddingBottom;}')
    assert "px" in paddingBottom, f"Could not get padding bottom for operator {target_value}"
    paddingBottom = int(paddingBottom.replace("px", ""))

    def strict_round(num):
        return int(num + (0.5 if num > 0 else -0.5))
    fontSize = strict_round(fontSize * 1.2)
    # Calculate the height of the operator
    height = fontSize + marginTop + marginBottom + paddingTop + paddingBottom

    bbox = selector.bounding_box()
    x = bbox["x"] + bbox["width"] / 2
    y = bbox["y"] + bbox["height"] + height / 2 + nth * height
    page.mouse.click(x, y, perform=False, use_pyautogui=True)

    x = bbox["x"] + bbox["width"] / 2
    y = bbox["y"] + bbox["height"] / 2
    page.mouse.move(x, y, record=False)
    page.mouse.click(x, y, record=False)

    selector.select_option(target_value, record=False)
    
def is_right_option_selected(page, selector, target_value, use_text_content=False):
    import pdb; pdb.set_trace()
    if use_text_content:
        value = selector.evaluate("el => el.options[el.selectedIndex].textContent")
    else:
        value = selector.get_attribute("value")
    if value == target_value:
        return True
    else:
        return False