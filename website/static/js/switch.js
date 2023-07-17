/*!
  * Bootstrap custom switch v5.1.0 (https://getbootstrap.com/)
  * @copyright 2021 The Bootstrap Authors
  * @license MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
  *//* eslint-disable no-unused-vars */
(function () {
    /**
     * ------------------------------------------------------------------------
     * Constants
     * ------------------------------------------------------------------------
     */
    var ClassName = {
        SWITCH: 'custom-switch',
        INPUT: 'custom-control-input',
        LABEL: 'custom-control-label',
        SWITCH_INPUT: 'custom-switch-input',
        SWITCH_LABEL: 'custom-switch-label',
        SWITCH_INDICATOR: 'custom-switch-indicator'
    }

    /**
     * ------------------------------------------------------------------------
     * Class Definition
     * ------------------------------------------------------------------------
     */
    var CustomSwitch = function (element) {
        this._element = element
        this._init()
    }

    // Public
    CustomSwitch.prototype.toggle = function () {
        if (this._element.disabled || this._element.classList.contains('disabled')) {
            return
        }

        var checked = !this._element.checked
        this._element.checked = checked
        this._element.dispatchEvent(new Event('change'))

        this._update()
    }

    CustomSwitch.prototype.dispose = function () {
        this._element = null
    }

    // Private
    CustomSwitch.prototype._init = function () {
        var _this = this

        if (this._element.classList.contains(ClassName.SWITCH_INPUT)) {
            throw new Error('CustomSwitch: Input element is already initialized as a custom switch.')
        }

        // Hide the input element
        this._element.hidden = true

        // Create the switch structure
        this._createSwitch()

        // Attach event listeners
        this._element.addEventListener('change', function () {
            return _this._update()
        })
    }

    CustomSwitch.prototype._createSwitch = function () {
        var switchContainer = document.createElement('label')
        switchContainer.classList.add(ClassName.SWITCH)
        switchContainer.classList.add('form-switch')
        switchContainer.classList.add('user-select-none')

        var switchInput = document.createElement('input')
        switchInput.type = 'checkbox'
        switchInput.classList.add(ClassName.INPUT)
        switchInput.classList.add(ClassName.SWITCH_INPUT)

        switchInput.checked = this._element.checked

        var switchLabel = document.createElement('label')
        switchLabel.classList.add(ClassName.LABEL)
        switchLabel.classList.add(ClassName.SWITCH_LABEL)

        var switchIndicator = document.createElement('span')
        switchIndicator.classList.add(ClassName.SWITCH_INDICATOR)

        switchContainer.appendChild(switchInput)
        switchContainer.appendChild(switchLabel)
        switchLabel.appendChild(switchIndicator)

        this._element.parentNode.insertBefore(switchContainer, this._element)
        switchLabel.appendChild(this._element)
    }

    CustomSwitch.prototype._update = function () {
        var checked = this._element.checked

        var switchContainer = this._element.parentNode
        var switchLabel = this._element.parentNode.querySelector('.' + ClassName.SWITCH_LABEL)
        var switchIndicator = this._element.parentNode.querySelector('.' + ClassName.SWITCH_INDICATOR)

        if (checked) {
            switchContainer.classList.add('active')
            switchIndicator.classList.add('active')
            switchLabel.classList.add('active')
        } else {
            switchContainer.classList.remove('active')
            switchIndicator.classList.remove('active')
            switchLabel.classList.remove('active')
        }
    }

    /**
     * ------------------------------------------------------------------------
     * jQuery
     * ------------------------------------------------------------------------
     */
    var $ = window.jQuery

    if ($) {
        var JQUERY_NO_CONFLICT = $.fn[ClassName.SWITCH]
        $.fn[ClassName.SWITCH] = function () {
            return this.each(function () {
                new CustomSwitch(this)
            })
        }
        $.fn[ClassName.SWITCH].Constructor = CustomSwitch
        $.fn[ClassName.SWITCH].noConflict = function () {
            $.fn[ClassName.SWITCH] = JQUERY_NO_CONFLICT
            return this
        }
    }

    // Initialize the custom switch for elements with the "data-toggle" attribute
    document.addEventListener('DOMContentLoaded', function () {
        var switchElements = document.querySelectorAll('[data-toggle="switch"]')
        for (var i = 0; i < switchElements.length; i++) {
            new CustomSwitch(switchElements[i])
        }
    })
})()
