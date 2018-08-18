<template>
  <div>
    <li >
      <a class="section" href="#">
        <i class="fas fa-signature fa-lg"></i> Plot
        <i class="fas fa-caret-down"></i></a>
    </li>
    <template v-for="(message, key) in messages">
      <li >
        <a class="section" href="#">
          <i class="fas fa-signature fa-lg"></i> {{key}}
          <i class="fas fa-caret-down"></i></a>
      </li>
      <template v-for="item in message">
        <li class="msgfield">
          <a href="#">
             {{item}}
          </a>
        </li>
        </template>
    </template>

  </div>
</template>
<script>
export default {
  name: 'message-menu',
  data () {
    return {
      msg: 'Batata',
      messages: {batata: ['doce', 'azul', 'penis']}
    }
  },
  created(){
    this.$eventHub.$on("messages", this.handleMessages)
  },
  beforeDestroy(){
    this.$eventHub.$off("messages")
  },
  methods: {
    handleMessages (messages){
      console.log(this)
      let newMessages = {}
      for (let messageType of Object.keys(messages)) {
        newMessages[messageType] = this.getMessageNumericField(messages[messageType][0])
      }
      this.messages = newMessages
      console.log(newMessages)
    },
    getMessageNumericField(message)
    {
      let numberFields = []
      for (let field of message.fieldnames) {
        if (!isNaN(message[field])) {
          numberFields.push(field)
        }
      }
      return numberFields
    }
  }
}
</script>
<style scoped>

    .nav-side-menu ul,
    .nav-side-menu li {
        list-style: none;
        padding: 0px;
        margin: 0px;
        line-height: 35px;
        cursor: pointer;
        /*
          .collapsed{
             .arrow:before{
                       font-family: FontAwesome;
                       content: "\f053";
                       display: inline-block;
                       padding-left:10px;
                       padding-right: 10px;
                       vertical-align: middle;
                       float:right;
                  }
           }
      */
    }

    .nav-side-menu ul .sub-menu li.active a,
    .nav-side-menu li .sub-menu li.active a {
        color: #d19b3d;
    }

    .nav-side-menu ul .sub-menu li,
    .nav-side-menu li .sub-menu li {
        background-color: #181c20;
        border: none;
        line-height: 28px;
        border-bottom: 1px solid #23282e;
        margin-left: 0px;
    }

    .nav-side-menu ul .sub-menu li:hover,
    .nav-side-menu li .sub-menu li:hover {
        background-color: #020203;
    }

    .nav-side-menu ul .sub-menu li:before,
    .nav-side-menu li .sub-menu li:before {
        font-family: FontAwesome;
        content: "\f105";
        display: inline-block;
        padding-left: 10px;
        padding-right: 10px;
        vertical-align: middle;
    }

    .nav-side-menu li {
        padding-left: 0px;
        border-left: 3px solid #2e353d;
        border-bottom: 1px solid #23282e;
    }

    .nav-side-menu li a {
        text-decoration: none;
        color: #e1ffff;
    }

    .nav-side-menu li a i {
        padding-left: 10px;
        width: 20px;
        padding-right: 20px;
    }

    .nav-side-menu li:hover {
        border-left: 3px solid #d19b3d;
        background-color: #4f5b69;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    @media (max-width: 767px) {

        main {
            height: 90%;
            margin-top: 50px;
        }
    }

    @media (min-width: 767px) {

        main {
            height: 100%;
        }
    }

    body {
        margin: 0px;
        padding: 0px;
    }

    i {
        margin: 10px;
    }

    ::-webkit-scrollbar {
        width: 12px;
        background-color: rgba(0, 0, 0, 0);
    }

    ::-webkit-scrollbar-thumb {
        border-radius: 5px;
        -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        background-color: #1c437f;
    }
  li.msgfield {
    line-height: 20px;
  }

</style>
