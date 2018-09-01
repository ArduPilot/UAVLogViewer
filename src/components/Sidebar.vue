<template>
    <div class="nav-side-menu col-md-3 col-lg-2">
        <div class="brand">TLog Viewer</div>
        <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>
        <div class="menu-list">
            <b-collapse visible id="menucontent" class="menu-content collapse out">
              <message-menu />
                <Dropzone/>
            </b-collapse>
        </div>
    </div>
</template>
<script>
import Dropzone from './SideBarFileManager'
import MessageMenu from './SideBarMessageMenu'

export default {
  name: 'sidebar',
  components: {MessageMenu, Dropzone}
}
</script>
<style>
    .nav-side-menu {
        overflow-x: hidden;
        font-family: verdana;
        font-size: 14px;
        font-weight: 200;
        background-color: #2e353d;
        position: fixed;
        top: 0px;
        /*width: 300px;*/
        height: 100%;
        color: #e1ffff;
    }

    .nav-side-menu .brand {
        background-color: #23282e;
        line-height: 50px;
        display: block;
        text-align: center;
        font-size: 17px;
        font-weight: bold;
    }

    .nav-side-menu .toggle-btn {
        display: none;
    }

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
        .nav-side-menu {
            position: fixed;
            width: 100%;
            margin-bottom: 10px;
            height: auto;
            max-height: 100%;
            z-index: 1002;
        }

        .nav-side-menu .toggle-btn {
            display: block;
            cursor: pointer;
            position: absolute;
            right: 10px;
            top: 0px;
            z-index: 10 !important;
            padding: 3px;
            background-color: #ffffff;
            color: #000;
            height: auto;
            width: 40px;
            text-align: center;
            -webkit-border-radius: 3px;
            -moz-border-radius: 3px;
            border-radius: 3px;
        }

        .brand {
            text-align: left !important;
            font-size: 22px;
            padding-left: 20px;
            line-height: 50px !important;
        }

        main {
            height: 90%;
            margin-top: 50px;
        }
    }

    @media (min-width: 767px) {
        .nav-side-menu .menu-list .menu-content {
            display: block;
            height: 100%;
        }

        main {
            height: 100%;
        }
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

    .custom-control-inline {
      margin-right: 0;
    }
</style>
