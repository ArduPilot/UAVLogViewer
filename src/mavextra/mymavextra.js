
// const key = ''
// const last_value = 0
window.named = (NAMED_VALUE_FLOAT, key) => {
    if (NAMED_VALUE_FLOAT.name.startsWith(key)) {
        return NAMED_VALUE_FLOAT.value
    }
    return null
}
